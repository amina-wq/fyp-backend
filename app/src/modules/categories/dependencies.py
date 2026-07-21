# Programmer Name: Rakhmatullayeva Amina
# Program Name: FoodTrack
# Description: FastAPI dependency providers for the food category service.
# First Written on: Wednesday, 01-Jul-2026
# Edited on: Wednesday, 01-Jul-2026

from src.modules.categories.services import FoodCategoryService


def get_food_category_service() -> FoodCategoryService:
    return FoodCategoryService()
