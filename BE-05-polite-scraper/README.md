# BE-05: The Polite Scraper

A Python web-scraping pipeline for the Books to Scrape practice website.

## Target Classification

- **Target:** https://books.toscrape.com/
- **Purpose:** Practice collecting and validating book catalogue data.
- **Scope:** The first three catalogue pages and their 60 unique book detail pages.
- **Data collected:** Book title, product URL, price, availability, rating, description, source page, and fetch timestamp.
- **Politeness:** Identify the scraper, use request timeouts, cache responses, and wait at least 500 ms between real requests.
- **Validation:** Validate records before writing them to JSON. Store invalid records and their error reasons separately.

### Responsible Use

I will not reuse this code on another site without checking its rules and terms first.