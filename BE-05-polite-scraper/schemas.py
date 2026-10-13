from pydantic import BaseModel, HttpUrl, Field


class RawBook(BaseModel):
    title: str
    product_url: HttpUrl
    price_text: str
    availability_text: str
    rating_text: str
    description: str | None = None
    source_page: str
    fetched_at: str


class Book(RawBook):
    price_gbp: float = Field(ge=0)