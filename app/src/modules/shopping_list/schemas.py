from datetime import datetime

from pydantic import BaseModel, Field
from src.modules.categories.schemas import FoodCategoryNestedSchema
from src.modules.inventory.models import InventoryUnits
from src.modules.shopping_list.models import ShoppingListSource


class ShoppingListItemCreateSchema(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    category_id: str
    amount: float | None = Field(default=None, gt=0)
    unit: InventoryUnits | None = None
    source: ShoppingListSource = ShoppingListSource.MANUAL
    source_id: str | None = None


class ShoppingListItemUpdateSchema(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    category_id: str | None = None
    amount: float | None = Field(default=None, gt=0)
    unit: InventoryUnits | None = None
    is_checked: bool | None = None


class ShoppingListItemResponseSchema(BaseModel):
    id: str
    user_id: str
    name: str
    category: FoodCategoryNestedSchema
    amount: float | None = None
    unit: InventoryUnits | None = None
    is_checked: bool
    source: ShoppingListSource
    source_id: str | None = None
    added_at: datetime
    updated_at: datetime
