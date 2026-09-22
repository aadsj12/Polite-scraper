from pathlib import Path

import requests


URL = "https://books.toscrape.com/catalogue/page-1.html"
CACHE_FILE = Path("cache/catalogue-page-1.html")

HEADERS = {
    "User-Agent": "FlyRankInternship-A9/1.0"
}


def fetch_page():
    if CACHE_FILE.exists():
        html = CACHE_FILE.read_text(encoding="utf-8")

        print(f"CACHE HIT {URL}")
        print(f"bytes={len(html.encode('utf-8'))}")

        return html

    print(f"FETCH {URL}")

    response = requests.get(
        URL,
        headers=HEADERS,
        timeout=10
    )

    print(f"status={response.status_code}")

    if response.status_code != 200:
        raise RuntimeError(
            f"Failed to fetch page: status={response.status_code}"
        )

    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(response.text, encoding="utf-8")

    print(f"bytes={len(response.content)}")

    return response.text


if __name__ == "__main__":
    fetch_page()