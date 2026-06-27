from datetime import UTC, datetime
from enum import Enum

from beanie import Document
from pydantic import BaseModel, Field
from pymongo import ASCENDING, IndexModel


class RecipeIngredientAvailability(str, Enum):
    AVAILABLE = 'available'
    MISSING = 'missing'
    INSUFFICIENT = 'insufficient'
    UNKNOWN_AMOUNT = 'unknown_amount'


class RecipeIngredientDetail(BaseModel):
    id: int | None = None
    name: str
    amount: float = 0
    unit: str = ''


class RecipeStepDetail(BaseModel):
    number: int
    step: str


class Recipe(Document):
    spoonacular_id: int
    title: str
    image: str | None = None

    ingredient_ids: list[int] = Field(default_factory=list)
    ingredient_names: list[str] = Field(default_factory=list)

    details_fetched: bool = False
    ready_in_minutes: int | None = None
    servings: int | None = None
    calories: float | None = None
    ingredients: list[RecipeIngredientDetail] = Field(default_factory=list)
    steps: list[RecipeStepDetail] = Field(default_factory=list)

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = 'recipes'
        indexes = [  # noqa: RUF012
            IndexModel(
                [('spoonacular_id', ASCENDING)],
                unique=True,
            ),
        ]


class RecipeQuery(Document):
    query: str
    ingredients: list[str] = Field(default_factory=list)
    recipe_ids: list[int] = Field(default_factory=list)

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = 'recipe_queries'
        indexes = [  # noqa: RUF012
            IndexModel(
                [('query', ASCENDING)],
                unique=True,
            ),
        ]
