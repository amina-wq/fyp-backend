# Programmer Name: Rakhmatullayeva Amina
# Program Name: FoodTrack
# Description: FastAPI dependency providers for the shopping list service.
# First Written on: Tuesday, 23-Jun-2026
# Edited on: Tuesday, 23-Jun-2026

from src.modules.shopping_list.services import ShoppingListService


def get_shopping_list_service() -> ShoppingListService:
    return ShoppingListService()
