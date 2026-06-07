from src.modules.inventory.services import InventoryService


def get_inventory_service() -> InventoryService:
    return InventoryService()
