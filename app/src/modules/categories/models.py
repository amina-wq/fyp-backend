# Programmer Name: Rakhmatullayeva Amina
# Program Name: FoodTrack
# Description: Beanie FoodCategory document model.
# First Written on: Wednesday, 01-Jul-2026
# Edited on: Wednesday, 01-Jul-2026

from datetime import UTC, datetime
from typing import Annotated

from beanie import Document, Indexed
from pydantic import Field


class FoodCategory(Document):
    key: Annotated[str, Indexed(unique=True)]
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=300)
    icon_url: str | None = None
    color_hex: str | None = Field(default=None, max_length=20)
    is_active: bool = True
    is_default: bool = False
    sort_order: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = 'food_categories'
