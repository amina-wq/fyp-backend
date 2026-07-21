# Programmer Name: Rakhmatullayeva Amina
# Program Name: FoodTrack
# Description: FastAPI dependency providers for the inventory service.
# First Written on: Sunday, 07-Jun-2026
# Edited on: Sunday, 07-Jun-2026

from src.modules.inventory.services import InventoryService


def get_inventory_service() -> InventoryService:
    return InventoryService()
