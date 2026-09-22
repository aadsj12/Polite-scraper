# Standard library imports
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

# Third-party imports
import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, ValidationError


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

# Start from the first catalogue page.
URL = "https://books.toscrape.com/catalogue/page-1.html"

# Identifiable user agent for polite scraping.
HEADERS = {
    "User-Agent": "FlyRankInternship-A9/1.0"
}


# ---------------------------------------------------------
# Custom errors
# ---------------------------------------------------------

class FetchError(Exception):
    """Raised when a page cannot be fetched successfully."""
    pass


# ---------------------------------------------------------
# Data validation model
# ---------------------------------------------------------

class Book(BaseModel):
    """Schema for a cleaned and validated book record."""

    title: str
    product_url: str
    price_text: str
    price_gbp: float
    availability_text: str
    rating_text: str
    description: str | None
    source_page: str
    fetched_at: str


# ---------------------------------------------------------
# Fetching and caching
# ---------------------------------------------------------

def fetch_page(url, cache_file):
    """
    Fetch a page or return its cached HTML.

    Politeness/failure rules:
    - Use cached HTML when available.
    - Wait at least 0.5 seconds before a real request.
    - Use a 10-second timeout.
    - Retry a timeout once.
    - Retry a 5xx response once.
    - Do not retry 403 or 404 responses.
    """

    # Avoid another network request if we already have this page.
    if cache_file.exists():
        html = cache_file.read_text(encoding="utf-8")

        print(f"CACHE HIT {url}")
        print(f"bytes={len(html.encode('utf-8'))}")

        return html

    print(f"FETCH {url}")

    # Two attempts maximum:
    # one original request + one possible retry.
    for attempt in range(2):

        # Polite delay before every real network request.
        time.sleep(0.5)

        try:
            response = requests.get(
                url,
                headers=HEADERS,
                timeout=10
            )

        except requests.Timeout:
            # Retry the first timeout once.
            if attempt == 0:
                print(f"RETRY {url}")
                continue

            # Second timeout becomes a recorded failure.
            raise FetchError(
                f"Failed to fetch {url}: timeout after retry"
            )

        print(f"status={response.status_code}")

        # 403 and 404 should not be retried.
        if response.status_code in (403, 404):
            raise FetchError(
                f"Failed to fetch {url}: "
                f"status={response.status_code}"
            )

        # Retry a server-side 5xx error once.
        if 500 <= response.status_code < 600:
            if attempt == 0:
                print(f"RETRY {url}")
                continue

            raise FetchError(
                f"Failed to fetch {url}: "
                f"status={response.status_code}"
            )

        # Any other unexpected HTTP response is treated as a failure.
        if response.status_code != 200:
            raise FetchError(
                f"Failed to fetch {url}: "
                f"status={response.status_code}"
            )

        # Explicitly decode the page as UTF-8.
        # This prevents values such as £51.77 becoming Â£51.77.
        response.encoding = "utf-8"

        # Create the cache directory if necessary.
        cache_file.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        # Save successful HTML locally.
        cache_file.write_text(
            response.text,
            encoding="utf-8"
        )

        print(f"bytes={len(response.content)}")

        return response.text

    # Defensive fallback. Normally unreachable.
    raise FetchError(f"Failed to fetch {url}")


# ---------------------------------------------------------
# Parsing
# ---------------------------------------------------------

def parse_book_page(html, product_url, source_page):
    """
    Extract the required raw fields from one book detail page.
    """

    soup = BeautifulSoup(html, "html.parser")

    # Required fields.
    title = soup.select_one(
        "div.product_main h1"
    ).get_text(strip=True)

    price_text = soup.select_one(
        "p.price_color"
    ).get_text(strip=True)

    availability_text = soup.select_one(
        "p.instock.availability"
    ).get_text(" ", strip=True)

    # The rating is stored in a class such as:
    # <p class="star-rating Three">
    rating_element = soup.select_one("p.star-rating")
    rating_text = rating_element.get("class")[1]

    # Description is optional.
    description_element = soup.select_one(
        "#product_description"
    )

    if description_element:
        description = (
            description_element
            .find_next_sibling("p")
            .get_text(" ", strip=True)
        )
    else:
        description = None

    # Return the raw scraped record.
    return {
        "title": title,
        "product_url": product_url,
        "price_text": price_text,
        "availability_text": availability_text,
        "rating_text": rating_text,
        "description": description,
        "source_page": source_page,
        "fetched_at": datetime.now(
            timezone.utc
        ).isoformat(),
    }


# ---------------------------------------------------------
# Cleaning and validation
# ---------------------------------------------------------

def normalize_price(price_text):
    """
    Convert a price such as '£51.77' into the float 51.77.
    """

    return float(
        price_text.replace("£", "").strip()
    )


def validate_book(raw_book):
    """
    Add the normalized price and validate the complete
    record using the Pydantic Book schema.
    """

    cleaned_book = raw_book.copy()

    cleaned_book["price_gbp"] = normalize_price(
        raw_book["price_text"]
    )

    return Book(**cleaned_book)


# ---------------------------------------------------------
# Main scraper
# ---------------------------------------------------------

if __name__ == "__main__":

    # =====================================================
    # 1. Discover books from the first three catalogue pages
    # =====================================================

    current_url = URL
    all_book_urls = []
    catalogue_pages = 0

    while current_url and catalogue_pages < 3:
        catalogue_pages += 1

        # Give each catalogue page its own cache file.
        cache_file = Path(
            f"cache/catalogue-page-{catalogue_pages}.html"
        )

        html = fetch_page(
            current_url,
            cache_file
        )

        soup = BeautifulSoup(
            html,
            "html.parser"
        )

        # Extract the 20 book links on this catalogue page.
        book_links = soup.select(
            "article.product_pod h3 a"
        )

        for link in book_links:
            # Convert relative links into absolute URLs.
            book_url = urljoin(
                current_url,
                link["href"]
            )

            all_book_urls.append(book_url)

        # Follow the website's Next link rather than
        # manually constructing catalogue URLs.
        next_link = soup.select_one("li.next a")

        if next_link:
            current_url = urljoin(
                current_url,
                next_link["href"]
            )
        else:
            current_url = None

    # Remove duplicates while preserving URL order.
    unique_book_urls = list(
        dict.fromkeys(all_book_urls)
    )

    print(
        f"catalogue_pages={catalogue_pages}"
    )
    print(
        f"discovered={len(all_book_urls)}"
    )
    print(
        f"unique_urls={len(unique_book_urls)}"
    )


    # =====================================================
    # 2. Add one deliberate broken URL
    # =====================================================

    # Stage 5 requires us to prove that one broken page
    # does not crash the entire scraper.
    test_urls = unique_book_urls + [
        (
            "https://books.toscrape.com/catalogue/"
            "this-page-does-not-exist/index.html"
        )
    ]


    # =====================================================
    # 3. Scrape the 60 real books
    # =====================================================

    books = []
    failed_pages = []

    for index, book_url in enumerate(
        test_urls,
        start=1
    ):

        # Each URL gets its own cache file.
        book_cache_file = Path(
            f"cache/books/book-{index}.html"
        )

        try:
            book_html = fetch_page(
                book_url,
                book_cache_file
            )

            book = parse_book_page(
                book_html,
                book_url,
                URL
            )

            books.append(book)

            print(
                f"parsed_book={len(books)}/60"
            )

        except FetchError as error:
            # Store the failure and continue scraping.
            failed_pages.append({
                "url": book_url,
                "error": str(error),
            })

            print(
                f"FAILED {book_url}: {error}"
            )

    print(f"records={len(books)}")


    # =====================================================
    # 4. Save raw scraped records
    # =====================================================

    output_directory = Path("output")

    output_directory.mkdir(
        parents=True,
        exist_ok=True
    )

    raw_output_file = (
        output_directory / "raw-books.json"
    )

    with raw_output_file.open(
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            books,
            file,
            indent=2,
            ensure_ascii=False
        )

    print(f"saved={raw_output_file}")


    # =====================================================
    # 5. Normalize and validate records
    # =====================================================

    valid_books = []
    errors = []

    for raw_book in books:
        try:
            validated_book = validate_book(
                raw_book
            )

            valid_books.append(
                validated_book.model_dump()
            )

        except (ValidationError, ValueError) as error:
            # Invalid records are kept out of books.json.
            errors.append({
                "product_url": raw_book.get(
                    "product_url"
                ),
                "error": str(error),
            })

    print(
        f"valid_records={len(valid_books)}"
    )
    print(
        f"errors={len(errors)}"
    )


    # =====================================================
    # 6. Save validated books and validation errors
    # =====================================================

    books_output_file = (
        output_directory / "books.json"
    )

    errors_output_file = (
        output_directory / "errors.json"
    )

    with books_output_file.open(
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            valid_books,
            file,
            indent=2,
            ensure_ascii=False
        )

    with errors_output_file.open(
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            errors,
            file,
            indent=2,
            ensure_ascii=False
        )

    print(f"saved={books_output_file}")
    print(f"saved={errors_output_file}")


    # =====================================================
    # 7. Create the run report
    # =====================================================

    run_report = {
        "catalogue_pages": catalogue_pages,
        "discovered_urls": len(
            unique_book_urls
        ),
        "successful_records": len(
            valid_books
        ),
        "validation_errors": len(
            errors
        ),
        "failed_pages": failed_pages,
    }

    report_file = (
        output_directory / "run-report.json"
    )

    with report_file.open(
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            run_report,
            file,
            indent=2,
            ensure_ascii=False
        )

    print(
        f"failed_pages={len(failed_pages)}"
    )
    print(
        f"saved={report_file}"
    )