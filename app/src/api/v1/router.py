from fastapi import APIRouter
from src.modules.auth.api.v1.router import router as auth_router
from src.modules.categories.api.v1.router import router as categories_router
from src.modules.inventory.api.v1.router import router as inventory_router
from src.modules.products.api.v1.router import router as products_router
from src.modules.recipes.api.v1.router import router as recipes_router
from src.modules.shopping_list.api.v1.router import router as shopping_list_router

router = APIRouter(prefix='/api/v1')

router.include_router(
    auth_router,
    prefix='/auth',
    tags=['Auth'],
)

router.include_router(
    products_router,
    prefix='/products',
    tags=['Products'],
)


router.include_router(
    categories_router,
    prefix='/categories',
    tags=['Categories'],
)


router.include_router(
    inventory_router,
    prefix='/inventory',
    tags=['Inventory'],
)


router.include_router(
    shopping_list_router,
    prefix='/shopping-list',
    tags=['Shopping List'],
)

router.include_router(
    recipes_router,
    prefix='/recipes',
    tags=['Recipes'],
)
