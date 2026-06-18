from datetime import UTC, date, datetime
from enum import Enum
from typing import Annotated

from beanie import Document, Indexed, PydanticObjectId
from pydantic import BaseModel, Field
from src.core.enums import FoodCategory


class StorageLocation(str, Enum):
    FRIDGE = 'fridge'
    FREEZER = 'freezer'
    PANTRY = 'pantry'
    COUNTER = 'counter'
    OTHER = 'other'


class InventoryUnits(str, Enum):
    PCS = 'pcs'
    G = 'g'
    KG = 'kg'
    ML = 'ml'
    L = 'l'
    PACK = 'pack'
    BOTTLE = 'bottle'
    CAN = 'can'
    OTHER = 'other'


class InventoryStatus(str, Enum):
    ACTIVE = 'active'
    CONSUMED = 'consumed'
    WASTED = 'wasted'
    DELETED = 'deleted'


class ScheduledNotification(BaseModel):
    days_before: int
    scheduled_for: datetime
    is_sent: bool = False
    sent_at: datetime | None = None


class InventoryItem(Document):
    user_id: Annotated[PydanticObjectId, Indexed()]
    product_id: PydanticObjectId | None = None
    barcode: str | None = None
    custom_name: str | None = None
    category: FoodCategory = FoodCategory.OTHER
    notes: str | None = None
    item_image_url: str | None = None
    location: StorageLocation = StorageLocation.FRIDGE
    opened_at: datetime | None = None
    amount: float = Field(default=1, gt=0)
    unit: InventoryUnits = InventoryUnits.PCS
    expiration_date: date
    status: InventoryStatus = InventoryStatus.ACTIVE
    scheduled_notifications: list[ScheduledNotification] = Field(default_factory=list)
    added_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = 'inventory_items'
