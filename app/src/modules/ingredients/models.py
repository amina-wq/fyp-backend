from datetime import UTC, datetime

from beanie import Document
from pydantic import Field
from pymongo import ASCENDING, IndexModel


class IngredientNormalization(Document):
    raw: str
    tags: list[str] = Field(default_factory=list)
    normalized: str
    provider: str = 'gemini'
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = 'ingredient_normalizations'
        indexes = [  # noqa: RUF012
            IndexModel(
                [('raw', ASCENDING)],
                unique=True,
            ),
        ]
