# The Polite Scraper

A small Python web scraper built for the FlyRank Internship Backend Track.

The scraper collects book data from Books to Scrape, a public sandbox website designed for practising web scraping. It discovers the first three catalogue pages, visits all 60 book detail pages, validates the collected data, caches responses, handles page failures, and produces structured JSON output.

## Target classification

- **Target:** Books to Scrape (https://books.toscrape.com/)
- **Purpose:** Books to Scrape is a public sandbox designed for practising web scraping.
- **Scope:** Only the first 3 catalogue pages are scraped, covering 60 books.
- **robots.txt:** I checked https://books.toscrape.com/robots.txt and received a 404 response, so no robots file was found.
- **Why this is appropriate:** The website is specifically provided as a practice environment for web scraping.

I would not reuse this scraper on another website without first checking that site's robots.txt, terms, and scraping policies.

## What the scraper does

1. Fetches the first catalogue page.
2. Follows the site's `Next` links until three catalogue pages have been processed.
3. Discovers and deduplicates 60 book detail URLs.
4. Visits each book page and extracts the required fields.
5. Caches downloaded HTML so repeat runs do not unnecessarily request the same pages.
6. Normalizes book prices into numeric GBP values.
7. Validates cleaned records using Pydantic.
8. Separates valid records from validation errors.
9. Handles individual page failures without crashing the entire run.
10. Produces JSON data and a run report.

## Setup

Clone the repository and enter the project directory.

Create a virtual environment:

```bash
python3 -m venv venv
```

Activate it on macOS/Linux:

```bash
source venv/bin/activate
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

## Run

Run the scraper with:

```bash
python src/main.py
```

A first run fetches pages from the website and stores them in the local cache. Later runs use cached HTML where available.

## Output

The scraper creates files inside `output/`:

- `books.json` — validated, cleaned book records.
- `errors.json` — records that failed data validation.
- `raw-books.json` — raw scraped records before normalization.
- `run-report.json` — summary of the scraping run and failed pages.

The current successful run produces 60 validated book records.

## Data schema

Each validated book contains:

- `title` — book title
- `product_url` — canonical URL of the book page
- `price_text` — original price text from the website
- `price_gbp` — normalized numeric GBP price
- `availability_text` — availability text from the page
- `rating_text` — star rating text
- `description` — book description, or `null` if unavailable
- `source_page` — catalogue source page
- `fetched_at` — UTC timestamp showing when the record was fetched

Keeping both `price_text` and `price_gbp` preserves the original source value while also providing a machine-friendly numeric value.

## Politeness and caching

The scraper is deliberately limited to three catalogue pages and 60 books.

It uses:

- An identifiable user agent: `FlyRankInternship-A9/1.0`
- A 10-second request timeout
- At least a 0.5-second delay before real network requests
- Local HTML caching to avoid unnecessary repeat requests
- Only one retry for timeouts and 5xx server errors
- No retries for 403 or 404 responses

The `cache/` directory is excluded from Git using `.gitignore`.

## Failure handling

A failure on one book page does not terminate the entire scrape.

Timeouts and 5xx responses are retried once. A 403 or 404 response is not retried. Failed pages are recorded so that the rest of the dataset can still be processed.

As a deliberate failure test, the scraper includes one fake book URL that returns a 404 response. The scraper continues successfully and produces:

- 60 successful records
- 0 validation errors
- 1 failed page

The failure is documented in `output/run-report.json`.

## Validation

Pydantic is used to validate cleaned book records before they are written to the final dataset.

Valid records are written to:

`output/books.json`

Validation failures are written to:

`output/errors.json`

This prevents malformed records from silently entering the final dataset.

## Limitations

- The scraper is intentionally restricted to the first three catalogue pages.
- It is designed specifically around the HTML structure of Books to Scrape.
- Changes to the site's HTML structure could require the CSS selectors to be updated.
- The deliberate fake URL is included to demonstrate failure handling.
- The scraper does not attempt to bypass access restrictions or anti-scraping controls.

## Ethics

This project uses Books to Scrape because it is explicitly provided as a sandbox for web-scraping practice.

The scraper limits request volume, adds delays between real requests, caches downloaded pages, and respects HTTP failures rather than attempting to bypass them.

Before adapting this code to another website, I would check that site's robots.txt, terms of service, and any relevant API or data-use policies.