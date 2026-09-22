from pathlib import Path

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time


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

    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(response.text, encoding="utf-8")

    print(f"bytes={len(response.content)}")

    return response.text


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