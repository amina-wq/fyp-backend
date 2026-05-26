from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Annotated
from beanie import Document, Indexed
from pydantic import Field

class ProductSource(str, Enum):
    OPEN_FOOD_FACTS = 'off'
    MANUAL = 'manual'
    SYSTEM = 'system'


class Product(Document):
    barcode: Annotated[Optional[str], Indexed(unique=True)] = None
    name: str
    brand: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    image_url: Optional[str] = None
    quantity: Optional[str] = None
    source: ProductSource = ProductSource.MANUAL
    is_verified: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = 'products'