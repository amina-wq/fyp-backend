from fastapi import APIRouter
from src.modules.auth.api.v1.router import router as auth_router
from src.modules.inventory.api.v1.router import router as inventory_router
from src.modules.products.api.v1.router import router as products_router

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
    inventory_router,
    prefix='/inventory',
    tags=['Inventory'],
)
