from pathlib import Path

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time
from datetime import datetime, timezone
import json
from pydantic import BaseModel, ValidationError


URL = "https://books.toscrape.com/catalogue/page-1.html"
CACHE_FILE = Path("cache/catalogue-page-1.html")

HEADERS = {
    "User-Agent": "FlyRankInternship-A9/1.0"
}


def fetch_page(url, cache_file):
    if cache_file.exists():
        html = cache_file.read_text(encoding="utf-8")

        print(f"CACHE HIT {url}")
        print(f"bytes={len(html.encode('utf-8'))}")

        return html

    print(f"FETCH {url}")

    time.sleep(0.5)

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=10
    )

    print(f"status={response.status_code}")

    if response.status_code != 200:
        raise RuntimeError(
            f"Failed to fetch page: status={response.status_code}"
        )

    response.encoding = "utf-8"

    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(response.text, encoding="utf-8")

    print(f"bytes={len(response.content)}")

    return response.text


class Book(BaseModel):
    title: str
    product_url: str
    price_text: str
    price_gbp: float
    availability_text: str
    rating_text: str
    description: str | None
    source_page: str
    fetched_at: str

def normalize_price(price_text):
    return float(price_text.replace("£", "").strip())

def validate_book(raw_book):
    cleaned_book = raw_book.copy()

    cleaned_book["price_gbp"] = normalize_price(
        raw_book["price_text"]
    )

    return Book(**cleaned_book)

def parse_book_page(html, product_url, source_page):
    soup = BeautifulSoup(html, "html.parser")

    title = soup.select_one("div.product_main h1").get_text(strip=True)
    price_text = soup.select_one("p.price_color").get_text(strip=True)
    availability_text = soup.select_one(
        "p.instock.availability"
    ).get_text(" ", strip=True)

    rating_element = soup.select_one("p.star-rating")
    rating_text = rating_element.get("class")[1]

    description_element = soup.select_one("#product_description")

    if description_element:
        description = description_element.find_next_sibling("p").get_text(
            " ", strip=True
        )
    else:
        description = None

    return {
        "title": title,
        "product_url": product_url,
        "price_text": price_text,
        "availability_text": availability_text,
        "rating_text": rating_text,
        "description": description,
        "source_page": source_page,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }

if __name__ == "__main__":
    current_url = URL
    all_book_urls = []
    catalogue_pages = 0

    while current_url and catalogue_pages < 3:
        catalogue_pages += 1

        cache_file = Path(
            f"cache/catalogue-page-{catalogue_pages}.html"
        )

        html = fetch_page(current_url, cache_file)
        soup = BeautifulSoup(html, "html.parser")

        book_links = soup.select("article.product_pod h3 a")

        for link in book_links:
            book_url = urljoin(current_url, link["href"])
            all_book_urls.append(book_url)

        next_link = soup.select_one("li.next a")

        if next_link:
            current_url = urljoin(URL, next_link["href"])
        else:
            current_url = None

    unique_book_urls = list(dict.fromkeys(all_book_urls))

    print(f"catalogue_pages={catalogue_pages}")
    print(f"discovered={len(all_book_urls)}")
    print(f"unique_urls={len(unique_book_urls)}")

    books = []

    for index, book_url in enumerate(unique_book_urls, start=1):
        book_cache_file = Path(f"cache/books/book-{index}.html")

        book_html = fetch_page(book_url, book_cache_file)

        book = parse_book_page(
            book_html,
            book_url,
            URL
        )

        books.append(book)

        print(f"parsed_book={index}/60")

    print(f"records={len(books)}")
    output_file = Path("output/raw-books.json")
output_file.parent.mkdir(parents=True, exist_ok=True)

with output_file.open("w", encoding="utf-8") as f:
    json.dump(books, f, indent=2, ensure_ascii=False)

print(f"saved={output_file}")
valid_books = []
errors = []

for raw_book in books:
    try:
        validated_book = validate_book(raw_book)
        valid_books.append(validated_book.model_dump())

    except (ValidationError, ValueError) as error:
        errors.append({
            "product_url": raw_book.get("product_url"),
            "error": str(error),
        })

print(f"valid_records={len(valid_books)}")
print(f"errors={len(errors)}")

books_output_file = Path("output/books.json")
errors_output_file = Path("output/errors.json")

with books_output_file.open("w", encoding="utf-8") as f:
    json.dump(valid_books, f, indent=2, ensure_ascii=False)

with errors_output_file.open("w", encoding="utf-8") as f:
    json.dump(errors, f, indent=2, ensure_ascii=False)

print(f"saved={books_output_file}")
print(f"saved={errors_output_file}")