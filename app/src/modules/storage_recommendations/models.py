from datetime import UTC, datetime
from enum import Enum
from typing import Annotated

from beanie import Document, Indexed
from pydantic import BaseModel, Field, field_validator
from src.modules.inventory.models import StorageLocation


class StorageState(str, Enum):
    WHOLE = 'whole'
    CUT = 'cut'
    RAW = 'raw'
    COOKED = 'cooked'
    OPENED = 'opened'
    UNOPENED = 'unopened'
    FRESH = 'fresh'


class StorageRule(BaseModel):
    location: StorageLocation
    state: StorageState
    recommended_days: Annotated[int, Field(gt=0, le=1095)]
    min_days: Annotated[int | None, Field(default=None, gt=0, le=1095)] = None
    max_days: Annotated[int | None, Field(default=None, gt=0, le=1095)] = None
    is_default: bool = False

    @field_validator('max_days')
    @classmethod
    def validate_max_days(cls, value: int | None, info) -> int | None:
        min_days = info.data.get('min_days')

        if value is not None and min_days is not None and value < min_days:
            raise ValueError('max_days cannot be lower than min_days')

        return value


class StorageRecommendation(Document):
    canonical_name: Annotated[str, Indexed(unique=True)]
    display_name: str
    category: str
    aliases: list[str] = Field(default_factory=list)
    normalized_aliases: Annotated[list[str], Indexed()] = Field(default_factory=list)
    rules: list[StorageRule] = Field(default_factory=list)
    source: str = 'gemini'
    is_verified: bool = False
    confidence: float = Field(default=0.6, ge=0, le=1)
    requires_clarification: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = 'storage_recommendations'
