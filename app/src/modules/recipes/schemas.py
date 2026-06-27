from pydantic import BaseModel, Field
from src.modules.inventory.models import InventoryUnits
from src.modules.recipes.models import RecipeIngredientAvailability


class RecipeSearchRequestSchema(BaseModel):
    number: int = Field(default=10, ge=1, le=20)


class RecipeResponseSchema(BaseModel):
    spoonacular_id: int
    title: str
    image: str | None = None
    match_score: float = 0.0
    used_ingredient_count: int = 0
    missed_ingredient_count: int = 0


class RecipeIngredientDetailResponseSchema(BaseModel):
    id: int | None = None
    name: str
    amount: float
    unit: str

    availability_status: RecipeIngredientAvailability
    inventory_item_id: str | None = None
    inventory_amount: float | None = None
    inventory_unit: InventoryUnits | None = None

    is_amount_comparable: bool = False


class RecipeStepDetailResponseSchema(BaseModel):
    number: int
    step: str


class RecipeDetailResponseSchema(BaseModel):
    spoonacular_id: int
    title: str
    image: str | None = None
    ready_in_minutes: int | None = None
    servings: int | None = None
    calories: float | None = None
    ingredients: list[RecipeIngredientDetailResponseSchema] = []
    steps: list[RecipeStepDetailResponseSchema] = []
