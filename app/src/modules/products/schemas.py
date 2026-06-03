from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, field_validator
from src.modules.products.models import ProductSource


class ManualProductCreateSchema(BaseModel):
    barcode: Annotated[str | None, Field(default=None, max_length=50)] = None
    name: Annotated[str, Field(min_length=1, max_length=150)]
    brand: Annotated[str | None, Field(default=None, max_length=100)] = None
    tags: list[str] = Field(default_factory=list)
    image_url: str | None = None
    quantity: Annotated[str | None, Field(default=None, max_length=50)] = None

    @field_validator('barcode')
    @classmethod
    def validate_barcode(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = value.strip()

        if not value:
            return None

        if ' ' in value:
            raise ValueError('Barcode cannot contain spaces')

        return value

    @field_validator('tags')
    @classmethod
    def validate_tags(cls, value: list[str]) -> list[str]:
        return [tag.strip().lower() for tag in value if tag.strip()]


class ProductResponseSchema(BaseModel):
    id: str
    barcode: str | None = None
    name: str
    brand: str | None = None
    tags: list[str] = Field(default_factory=list)
    image_url: str | None = None
    quantity: str | None = None
    source: ProductSource
    is_verified: bool
    created_at: datetime
    updated_at: datetime
