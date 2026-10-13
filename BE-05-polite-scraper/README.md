# BE-05: The Polite Scraper

A Python scraping pipeline that collects book catalogue data from the Books to Scrape practice website, validates records with Pydantic, and saves structured JSON output.

## 1. Target Classification

- **Target:** https://books.toscrape.com/
- **Purpose:** Practice extracting structured catalogue data from a website designed for scraping practice.
- **Scope:** The first three catalogue pages and their book detail pages.
- **Expected records:** 60 unique book URLs.
- **Data collected:** Title, product URL, raw price, availability, rating, description, source catalogue page, fetch timestamp, and normalized price in GBP.
- **Robots.txt check:** A request to `https://books.toscrape.com/robots.txt` returned HTTP 404 Not Found on 13 October 2026. This only establishes that the file was unavailable at that URL during the check; it is not blanket permission to scrape.
- **Responsible use:** This project is limited to the practice website and should not be reused on another website without checking its rules and terms first.

## 2. Features

- Identifiable User-Agent.
- Request timeout and HTTP status validation.
- At least 500 ms between real HTTP requests.
- Local HTML caching to avoid unnecessary repeat requests.
- One retry for request timeouts and HTTP 5xx responses.
- No retry for HTTP 403 or 404 responses.
- Relative-to-absolute URL resolution and duplicate URL removal.
- Raw price preservation and numeric GBP price normalization.
- Pydantic validation before records are written.
- Separate error output for failed records.
- Run report with record counts, fetch/cache statistics, duration, and failed-page details.
- Automated tests for parsing, validation, duplicate URLs, malformed HTML, and failure recovery.

## 3. Data Schema

Each successful record in `output/books.json` contains:

| Field | Description |
|---|---|
| `title` | Book title |
| `product_url` | Absolute URL of the book detail page |
| `price_text` | Original price text |
| `availability_text` | Availability text |
| `rating_text` | Star rating as text |
| `description` | Description, or `null` if missing |
| `source_page` | Catalogue page associated with discovery |
| `fetched_at` | UTC timestamp |
| `price_gbp` | Normalized numeric price in GBP |

## 4. Installation and Execution

Run these commands from the scraper directory.

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Run the scraper:

```powershell
python scraper.py
```

Run the automated tests:

```powershell
python -m pytest -v .\tests
```

The scraper creates the `output` directory automatically.

## 5. Output Files

- `output/books.json` — validated book records.
- `output/errors.json` — failed records and their error reasons.
- `output/run-report.json` — execution statistics and failure details.

Cached HTML is stored under `cache/` and should not be committed to the repository.

## 6. Politeness and Ethics

- Prefer an official API when one is available and suitable.
- Identify the scraper with a User-Agent.
- Apply request timeouts and rate limiting.
- Cache responses to reduce repeated requests.
- Do not bypass logins, paywalls, access controls, or anti-bot restrictions.
- Collect only the data needed for the stated purpose.
- Check the target website's current rules and terms before reuse.

I will not reuse this code on another site without checking its rules and terms first.

## 7. Why No Browser Automation?

The required catalogue and book details are available in the HTML returned by ordinary HTTP requests. Requests and BeautifulSoup are sufficient for this task, so browser automation would add unnecessary complexity and resource usage.
