from src.modules.categories.services import FoodCategoryService


def get_food_category_service() -> FoodCategoryService:
    return FoodCategoryService()
