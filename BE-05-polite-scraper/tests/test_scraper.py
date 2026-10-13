
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
