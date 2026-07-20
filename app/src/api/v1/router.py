from fastapi import APIRouter, Depends
from src.core.rate_limiter import rate_limit
from src.modules.admin.api.v1.categories_router import router as admin_categories_router
from src.modules.auth.api.v1.router import router as auth_router
from src.modules.categories.api.v1.router import router as categories_router
from src.modules.inventory.api.v1.router import router as inventory_router
from src.modules.notifications.api.v1.router import router as notifications_router
from src.modules.products.api.v1.router import router as products_router
from src.modules.recipes.api.v1.router import router as recipes_router
from src.modules.shopping_list.api.v1.router import router as shopping_list_router
from src.modules.storage_recommendations.api.v1.router import router as storage_recommendations_router

default_rate_limit = rate_limit(times=120, seconds=60, scope='api-default')

router = APIRouter(prefix='/api/v1', dependencies=[Depends(default_rate_limit)])

router.include_router(
    auth_router,
    prefix='/auth',
    tags=['Auth'],
)


router.include_router(
    admin_categories_router,
    prefix='/admin',
    tags=['Admin Categories'],
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

router.include_router(
    storage_recommendations_router,
    prefix='/storage',
    tags=['Storage Recommendations'],
)

router.include_router(
    notifications_router,
    prefix='/notifications',
    tags=['Notifications'],
)
