from src.modules.shopping_list.services import ShoppingListService


def get_shopping_list_service() -> ShoppingListService:
    return ShoppingListService()
