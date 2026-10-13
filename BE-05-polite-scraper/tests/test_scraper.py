
import pytest
from pydantic import ValidationError

import scraper
from schemas import Book, RawBook


def test_normalize_price():
    assert scraper.normalize_price("£51.77") == 51.77
    assert scraper.normalize_price(" £1,234.50 ") == 1234.50
    assert scraper.normalize_price("£0.00") == 0.00


def test_normalize_price_without_valid_number():
    with pytest.raises(ValueError):
        scraper.normalize_price("No price available")


def test_raw_book_validation():
    book = RawBook(
        title="Test Book",
        product_url="https://books.toscrape.com/catalogue/test-book_1/index.html",
        price_text="£10.99",
        availability_text="In stock",
        rating_text="Three",
        description="A test description",
        source_page="https://books.toscrape.com/",
        fetched_at="2026-10-13T08:00:00+00:00",
    )

    assert book.title == "Test Book"
    assert book.price_text == "£10.99"


def test_book_accepts_valid_price():
    book = Book(
        title="Test Book",
        product_url="https://books.toscrape.com/catalogue/test-book_1/index.html",
        price_text="£10.99",
        availability_text="In stock",
        rating_text="Three",
        description=None,
        source_page="https://books.toscrape.com/",
        fetched_at="2026-10-13T08:00:00+00:00",
        price_gbp=10.99,
    )

    assert book.price_gbp == 10.99


def test_book_rejects_negative_price():
    with pytest.raises(ValidationError):
        Book(
            title="Test Book",
            product_url="https://books.toscrape.com/catalogue/test-book_1/index.html",
            price_text="£10.99",
            availability_text="In stock",
            rating_text="Three",
            description=None,
            source_page="https://books.toscrape.com/",
            fetched_at="2026-10-13T08:00:00+00:00",
            price_gbp=-1.00,
        )


def test_extract_book_success(monkeypatch):
    html = """
    <html>
      <div class="product_main">
        <h1>Test Book</h1>
        <p class="price_color">£10.99</p>
        <p class="star-rating Three"></p>
        <p class="instock availability">
          <i class="icon-ok"></i>
          In stock (5 available)
        </p>
      </div>
      <div id="product_description"></div>
      <p>A test description.</p>
    </html>
    """

    monkeypatch.setattr(
        scraper,
        "fetch_page",
        lambda url: (html, False),
    )

    url = "https://books.toscrape.com/catalogue/test-book_1/index.html"
    source_page = "https://books.toscrape.com/"

    book = scraper.extract_book(url, source_page)

    assert book["title"] == "Test Book"
    assert book["product_url"] == url
    assert book["price_text"] == "£10.99"
    assert book["availability_text"] == "In stock (5 available)"
    assert book["rating_text"] == "Three"
    assert book["description"] == "A test description."
    assert book["source_page"] == source_page
    assert book["fetched_at"]


def test_extract_book_missing_required_fields(monkeypatch):
    html = "<html><body><h1>Incomplete Book</h1></body></html>"

    monkeypatch.setattr(
        scraper,
        "fetch_page",
        lambda url: (html, False),
    )

    with pytest.raises(ValueError, match="Required title or price field is missing"):
        scraper.extract_book(
            "https://books.toscrape.com/catalogue/incomplete_1/index.html",
            "https://books.toscrape.com/",
        )
def test_discover_catalogue_resolves_relative_urls_and_removes_duplicates(
    monkeypatch,
):
    page_one = """
    <html><body>
      <article class="product_pod">
        <h3><a href="catalogue/test-book_1/index.html">Book 1</a></h3>
      </article>
      <article class="product_pod">
        <h3><a href="catalogue/test-book_1/index.html">Book 1 duplicate</a></h3>
      </article>
      <li class="next"><a href="catalogue/page-2.html">Next</a></li>
    </body></html>
    """

    page_two = """
    <html><body>
      <article class="product_pod">
        <h3><a href="test-book_2_2/index.html">Book 2</a></h3>
      </article>
      <li class="next"><a href="page-3.html">Next</a></li>
    </body></html>
    """

    page_three = """
    <html><body>
      <article class="product_pod">
        <h3><a href="test-book_1/index.html">Book 1 duplicate</a></h3>
      </article>
    </body></html>
    """

    pages = {
        "https://books.toscrape.com/": page_one,
        "https://books.toscrape.com/catalogue/page-2.html": page_two,
        "https://books.toscrape.com/catalogue/page-3.html": page_three,
    }

    monkeypatch.setattr(
        scraper,
        "fetch_page",
        lambda url: (pages[url], True),
    )

    urls, page_count = scraper.discover_catalogue()

    assert page_count == 3
    assert len(urls) == 2
    assert len(set(urls)) == 2
    assert urls[0] == (
        "https://books.toscrape.com/catalogue/test-book_1/index.html"
    )
    assert urls[1] == (
        "https://books.toscrape.com/catalogue/test-book_2_2/index.html"
    )


def test_extract_book_missing_description_returns_none(monkeypatch):
    html = """
    <html><body>
      <div class="product_main">
        <h1>Book Without Description</h1>
        <p class="price_color">£10.99</p>
        <p class="star-rating Three"></p>
        <p class="instock availability">In stock</p>
      </div>
    </body></html>
    """

    monkeypatch.setattr(
        scraper,
        "fetch_page",
        lambda url: (html, True),
    )

    book = scraper.extract_book(
        "https://books.toscrape.com/catalogue/test-book_1/index.html",
        "https://books.toscrape.com/",
    )

    assert book["description"] is None


def test_extract_book_malformed_html_raises(monkeypatch):
    html = """
    <html><body>
      <div class="product_main">
        <h1>Incomplete Book</h1>
    """

    monkeypatch.setattr(
        scraper,
        "fetch_page",
        lambda url: (html, True),
    )

    with pytest.raises(
        ValueError,
        match="Required title or price field is missing",
    ):
        scraper.extract_book(
            "https://books.toscrape.com/catalogue/incomplete_1/index.html",
            "https://books.toscrape.com/",
        )


def test_main_continues_when_one_book_fails(monkeypatch, tmp_path):
    import json

    monkeypatch.setattr(scraper, "OUTPUT_DIR", tmp_path)

    urls = [
        f"https://books.toscrape.com/catalogue/test-book-{i}/index.html"
        for i in range(1, 61)
    ]

    monkeypatch.setattr(
        scraper,
        "discover_catalogue",
        lambda: (urls, 3),
    )

    def fake_extract_book(url, source_page):
        if url == urls[16]:
            raise ValueError("Simulated broken book page")

        return {
            "title": f"Test Book {url.split('-')[-1].split('/')[0]}",
            "product_url": url,
            "price_text": "£10.99",
            "availability_text": "In stock",
            "rating_text": "Three",
            "description": "Test description",
            "source_page": source_page,
            "fetched_at": "2026-10-13T08:00:00+00:00",
        }

    monkeypatch.setattr(scraper, "extract_book", fake_extract_book)

    scraper.main()

    books = json.loads((tmp_path / "books.json").read_text(encoding="utf-8"))
    errors = json.loads((tmp_path / "errors.json").read_text(encoding="utf-8"))
    report = json.loads((tmp_path / "run-report.json").read_text(encoding="utf-8"))

    assert len(books) == 59
    assert len(errors) == 1
    assert errors[0]["product_url"] == urls[16]
    assert "Simulated broken book page" in errors[0]["reason"]
    assert report["valid_records"] == 59
    assert report["invalid_records"] == 1
    assert report["failed_pages"] == 1
    assert report["failed_page_urls"] == [urls[16]]
