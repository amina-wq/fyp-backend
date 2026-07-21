# Programmer Name: Rakhmatullayeva Amina
# Program Name: FoodTrack
# Description: FastAPI dependency providers for the product service.
# First Written on: Wednesday, 03-Jun-2026
# Edited on: Wednesday, 03-Jun-2026

from src.modules.products.services import ProductService


def get_product_service() -> ProductService:
    return ProductService()
