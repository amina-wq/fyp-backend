from datetime import UTC, datetime
from enum import Enum
from typing import Annotated

from beanie import Document, Indexed
from pydantic import Field


class ProductSource(str, Enum):
    OPEN_FOOD_FACTS = 'off'
    MANUAL = 'manual'
    SYSTEM = 'system'


class Product(Document):
    barcode: Annotated[str | None, Indexed(unique=True, sparse=True)] = None
    name: str
    brand: str | None = None
    tags: list[str] = Field(default_factory=list)
    image_url: str | None = None
    quantity: str | None = None
    source: ProductSource = ProductSource.MANUAL
    is_verified: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = 'products'
