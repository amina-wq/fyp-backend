from typing import Annotated

from pydantic import BaseModel, Field
from src.modules.inventory.models import StorageLocation
from src.modules.storage_recommendations.models import StorageState


class StorageRecommendationRequestSchema(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=120)]
    category: Annotated[str | None, Field(default=None, max_length=50)] = None
    location: StorageLocation | None = None
    state: StorageState | None = None


class StorageRecommendationOptionSchema(BaseModel):
    location: StorageLocation
    state: StorageState
    recommended_days: int
    min_days: int | None = None
    max_days: int | None = None


class StorageRecommendationResponseSchema(BaseModel):
    input: str
    canonical_name: str
    display_name: str
    category: str
    recommended_days: int | None = None
    min_days: int | None = None
    max_days: int | None = None
    location: StorageLocation | None = None
    state: StorageState | None = None
    source: str
    confidence: Annotated[float, Field(ge=0, le=1)]
    is_verified: bool
    requires_clarification: bool = False
    options: list[StorageRecommendationOptionSchema] = Field(default_factory=list)
