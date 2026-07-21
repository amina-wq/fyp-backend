# Programmer Name: Rakhmatullayeva Amina
# Program Name: FoodTrack
# Description: Pydantic request/response schemas for inventory items.
# First Written on: Tuesday, 19-May-2026
# Edited on: Saturday, 18-Jul-2026

from datetime import date, datetime
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field, model_validator
from src.modules.categories.schemas import FoodCategoryNestedSchema
from src.modules.inventory.models import InventoryStatus, InventoryUnits, ScheduledNotification, StorageLocation


class ExpiryState(str, Enum):
    FRESH = 'fresh'
    EXPIRING = 'expiring'
    EXPIRED = 'expired'


class InventoryItemCreateSchema(BaseModel):
    product_id: str | None = None
    barcode: Annotated[str | None, Field(default=None, max_length=50)] = None
    custom_name: Annotated[str | None, Field(default=None, max_length=150)] | None = None
    category_id: str
    notes: Annotated[str | None, Field(default=None, max_length=500)] | None = None
    item_image_url: str | None = None
    location: StorageLocation = StorageLocation.FRIDGE
    amount: Annotated[float, Field(gt=0)] = 1
    unit: InventoryUnits = InventoryUnits.PCS
    expiration_date: date

    @model_validator(mode='after')
    def validate_product_reference(self) -> 'InventoryItemCreateSchema':
        if not self.product_id and not self.barcode and not self.custom_name:
            raise ValueError('Either product_id, barcode or custom name must be provided')

        return self


class InventoryItemUpdateSchema(BaseModel):
    custom_name: Annotated[str | None, Field(default=None, max_length=150)] = None
    category_id: str | None = None
    notes: Annotated[str | None, Field(default=None, max_length=500)] = None
    item_image_url: str | None = None
    location: StorageLocation | None = None
    amount: Annotated[float | None, Field(gt=0)] = None
    unit: InventoryUnits | None = None
    expiration_date: date | None = None


class InventoryItemResponseSchema(BaseModel):
    id: str
    user_id: str
    product_id: str | None = None
    barcode: str | None = None
    custom_name: str | None = None
    display_name: str
    item_image_url: str | None = None
    product_image_url: str | None = None
    product_brand: str | None = None
    category: FoodCategoryNestedSchema
    notes: str | None = None
    location: StorageLocation
    amount: float
    unit: InventoryUnits
    expiration_date: date
    best_before_date: date | None = None
    status: InventoryStatus
    expiry_state: ExpiryState
    scheduled_notifications: list[ScheduledNotification] = Field(default_factory=list)
    added_at: datetime
    updated_at: datetime


class InventoryStatsResponseSchema(BaseModel):
    expired_count: int
    expiring_tomorrow_count: int
    expiring_in_5_days_count: int
    fresh_count: int
