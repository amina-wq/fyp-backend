from datetime import UTC, datetime
from enum import Enum

from beanie import Document
from pydantic import Field
from pymongo import ASCENDING, IndexModel


class ProductSource(str, Enum):
    OPEN_FOOD_FACTS = 'off'
    MANUAL = 'manual'
    SYSTEM = 'system'


class Product(Document):
    barcode: str | None = None
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
        indexes = [  # noqa: RUF012
            IndexModel(
                [('barcode', ASCENDING)],
                unique=True,
                partialFilterExpression={
                    'barcode': {
                        '$type': 'string',
                    },
                },
            ),
        ]
