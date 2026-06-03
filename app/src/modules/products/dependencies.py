from src.modules.products.services import ProductService


def get_product_service() -> ProductService:
    return ProductService()
