# Programmer Name: Rakhmatullayeva Amina
# Program Name: FoodTrack
# Description: Beanie ShoppingListItem document model.
# First Written on: Tuesday, 19-May-2026
# Edited on: Wednesday, 01-Jul-2026

from datetime import UTC, datetime
from enum import Enum
from typing import Annotated

from beanie import Document, Indexed, PydanticObjectId
from pydantic import Field
from src.modules.inventory.models import InventoryUnits


class ShoppingListSource(str, Enum):
    MANUAL = 'manual'
    INVENTORY = 'inventory'


class ShoppingListItem(Document):
    user_id: Annotated[PydanticObjectId, Indexed()]
    name: str = Field(..., min_length=1, max_length=100)
    category_id: PydanticObjectId
    amount: float | None = Field(default=None, gt=0)
    unit: InventoryUnits | None = None
    is_checked: bool = False
    source: ShoppingListSource = ShoppingListSource.MANUAL
    source_id: str | None = None
    added_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = 'shopping_list_items'
