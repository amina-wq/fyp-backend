# Programmer Name: Rakhmatullayeva Amina
# Program Name: FoodTrack
# Description: FastAPI dependency providers for the recipe service.
# First Written on: Saturday, 27-Jun-2026
# Edited on: Saturday, 27-Jun-2026

from src.modules.recipes.services import RecipeService


def get_recipe_service() -> RecipeService:
    return RecipeService()
