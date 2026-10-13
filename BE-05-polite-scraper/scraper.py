from pathlib import Path
from urllib import response
from urllib.parse import urljoin, urlparse
from datetime import datetime, timezone
import json
import time
import re

import requests
from bs4 import BeautifulSoup

from schemas import RawBook, Book

BASE_URL = "https://books.toscrape.com/"
USER_AGENT = (
    "PlabonBasak-BE05/1.0 "
    "(+https://github.com/Plabon-Basak)"
)

PROJECT_DIR = Path(__file__).resolve().parent
CACHE_DIR = PROJECT_DIR / "cache"
OUTPUT_DIR = PROJECT_DIR / "output"

TIMEOUT_SECONDS = 10
MIN_REQUEST_INTERVAL = 0.5
MAX_CATALOGUE_PAGES = 3

_last_request_time = 0.0
PAGES_FETCHED = 0
CACHE_HITS = 0


def fetch_page(url: str) -> tuple[str, bool]:
    """Fetch a page or load its uniquely named cached HTML."""
    global _last_request_time, PAGES_FETCHED, CACHE_HITS

    parsed = urlparse(url)

    if url == BASE_URL:
        cache_path = CACHE_DIR / "catalogue-page-1.html"
    elif "/catalogue/page-" in parsed.path:
        cache_path = CACHE_DIR / Path(parsed.path).name
    else:
        book_slug = Path(parsed.path).parent.name
        cache_path = CACHE_DIR / "details" / f"{book_slug}.html"

    if cache_path.exists():
        html = cache_path.read_text(encoding="utf-8")
        CACHE_HITS += 1
        print(f"CACHE HIT: {url}")
        print(f"Response size: {len(html.encode('utf-8'))} bytes")
        return html, True

    for attempt in range(2):
        elapsed = time.monotonic() - _last_request_time

        if _last_request_time and elapsed < MIN_REQUEST_INTERVAL:
            time.sleep(MIN_REQUEST_INTERVAL - elapsed)

        print(f"FETCH: {url}")
        _last_request_time = time.monotonic()

        try:
            response = requests.get(
                url,
                headers={"User-Agent": USER_AGENT},
                timeout=TIMEOUT_SECONDS,
            )
        except requests.Timeout:
            if attempt == 0:
                print(f"RETRY after timeout: {url}")
                continue
            raise

        if response.status_code >= 500 and attempt == 0:
            print(
                f"RETRY after HTTP {response.status_code}: {url}"
            )
            continue

        response.raise_for_status()

        if response.status_code != 200:
            raise requests.HTTPError(
                f"Unexpected HTTP status: {response.status_code}",
                response=response,
            )

        response.encoding = "utf-8"
        html = response.text

        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(html, encoding="utf-8")

        PAGES_FETCHED += 1
        print(f"Response size: {len(response.content)} bytes")
        return html, False

    raise RuntimeError(f"Failed to fetch page after retry: {url}")


def discover_catalogue() -> tuple[list[str], int]:
    """Discover unique book URLs from three catalogue pages."""
    catalogue_url = BASE_URL
    visited_pages = set()
    book_urls = []
    page_count = 0

    while catalogue_url and page_count < MAX_CATALOGUE_PAGES:
        if catalogue_url in visited_pages:
            break

        visited_pages.add(catalogue_url)

        html, _ = fetch_page(catalogue_url)
        soup = BeautifulSoup(html, "html.parser")
        page_count += 1

        for link in soup.select("article.product_pod h3 a"):
            href = link.get("href")

            if href:
                book_url = urljoin(catalogue_url, href)

                if book_url not in book_urls:
                    book_urls.append(book_url)

        next_link = soup.select_one("li.next a")

        if next_link and next_link.get("href"):
            catalogue_url = urljoin(
                catalogue_url,
                next_link["href"],
            )
        else:
            catalogue_url = None

    return book_urls, page_count


def extract_book(url: str, source_page: str) -> dict:
    """Extract raw fields from a book detail page."""
    html, _ = fetch_page(url)
    soup = BeautifulSoup(html, "html.parser")

    title_tag = soup.select_one("div.product_main h1")
    price_tag = soup.select_one("p.price_color")
    availability_tag = soup.select_one(
        "p.instock.availability"
    )
    rating_tag = soup.select_one(
        "div.product_main p.star-rating"
    )
    description_tag = soup.select_one(
        "#product_description + p"
    )

    if title_tag is None or price_tag is None:
        raise ValueError(
            "Required title or price field is missing"
        )

    rating = ""

    if rating_tag:
        classes = rating_tag.get("class", [])
        rating = next(
            (
                name for name in classes
                if name != "star-rating"
            ),
            "",
        )

    return {
        "title": title_tag.get_text(strip=True),
        "product_url": url,
        "price_text": price_tag.get_text(strip=True),
        "availability_text": (
            availability_tag.get_text(" ", strip=True)
            if availability_tag else ""
        ),
        "rating_text": rating,
        "description": (
            description_tag.get_text(" ", strip=True)
            if description_tag else None
        ),
        "source_page": source_page,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }

def normalize_price(price_text: str) -> float:
    """Convert a GBP price string such as £51.77 to a number."""
    cleaned = price_text.strip().replace(",", "")
    match = re.search(r"\d+(?:\.\d{1,2})?", cleaned)

    if not match:
        raise ValueError(f"Invalid price: {price_text}")

    return round(float(match.group()), 2)

def main() -> None:
    started_at = datetime.now(timezone.utc)
    start_monotonic = time.monotonic()
    global PAGES_FETCHED, CACHE_HITS
    PAGES_FETCHED = 0
    CACHE_HITS = 0

    books = []
    errors = []
    failed_pages = []

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    urls, page_count = discover_catalogue()

    print(f"\nCatalogue pages visited: {page_count}")
    print(f"Discovered book URLs: {len(urls)}")
    print(f"Unique book URLs: {len(set(urls))}")

    for index, url in enumerate(urls, start=1):
        try:
            record = extract_book(url, BASE_URL)
            raw_book = RawBook.model_validate(record)

            normalized_record = raw_book.model_dump(mode="json")
            normalized_record["price_gbp"] = normalize_price(
                raw_book.price_text
            )

            validated = Book.model_validate(normalized_record)
            books.append(validated.model_dump(mode="json"))

            print(
                f"[{index}/{len(urls)}] OK: "
                f"{record['title']}"
            )

        except Exception as exc:
            errors.append({
                "product_url": url,
                "reason": str(exc),
            })

            failed_pages.append(url)

            print(
                f"[{index}/{len(urls)}] ERROR: "
                f"{url}: {exc}"
            )

    (OUTPUT_DIR / "books.json").write_text(
        json.dumps(
            books,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    (OUTPUT_DIR / "errors.json").write_text(
        json.dumps(
            errors,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    report = {
        "started_at": started_at.isoformat(),
        "duration_seconds": round(
            time.monotonic() - start_monotonic,
            2,
        ),
        "catalogue_pages_visited": page_count,
        "discovered_urls": len(urls),
        "valid_records": len(books),
        "invalid_records": len(errors),
        "failed_pages": len(failed_pages),
        "failed_page_urls": failed_pages,
        "pages_fetched": PAGES_FETCHED,
        "cache_hits": CACHE_HITS,
    }

    (OUTPUT_DIR / "run-report.json").write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    print("\n--- Extraction checkpoint ---")
    print(f"Valid records: {len(books)}")
    print(f"Invalid records: {len(errors)}")
    print(f"Output directory: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
