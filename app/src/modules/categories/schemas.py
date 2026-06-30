from datetime import datetime

from pydantic import BaseModel, Field


class FoodCategoryResponseSchema(BaseModel):
    id: str
    key: str
    name: str
    description: str | None = None
    icon_url: str | None = None
    color_hex: str | None = None
    is_active: bool
    is_default: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime


class FoodCategoryCreateSchema(BaseModel):
    key: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=300)
    icon_url: str | None = None
    color_hex: str | None = Field(default=None, max_length=20)
    sort_order: int = 0


class FoodCategoryUpdateSchema(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=300)
    icon_url: str | None = None
    color_hex: str | None = Field(default=None, max_length=20)
    is_active: bool | None = None
    sort_order: int | None = None
