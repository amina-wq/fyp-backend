from typing import Annotated

from fastapi import APIRouter, Depends, Path, status
from src.modules.auth.dependencies import get_current_admin_user
from src.modules.auth.models import User
from src.modules.categories.dependencies import get_food_category_service
from src.modules.categories.schemas import (
    FoodCategoryCreateSchema,
    FoodCategoryResponseSchema,
    FoodCategoryUpdateSchema,
)
from src.modules.categories.services import FoodCategoryService

router = APIRouter()


@router.get(
    '/categories',
    response_model=list[FoodCategoryResponseSchema],
    summary='Admin: get all food categories',
)
async def get_all_food_categories_for_admin(
    current_admin: Annotated[User, Depends(get_current_admin_user)],
    service: Annotated[FoodCategoryService, Depends(get_food_category_service)],
) -> list[FoodCategoryResponseSchema]:
    return await service.get_all_categories_for_admin()


@router.post(
    '/categories',
    response_model=FoodCategoryResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary='Admin: create food category',
)
async def create_food_category(
    data: FoodCategoryCreateSchema,
    current_admin: Annotated[User, Depends(get_current_admin_user)],
    service: Annotated[FoodCategoryService, Depends(get_food_category_service)],
) -> FoodCategoryResponseSchema:
    return await service.create_category(data)


@router.patch(
    '/categories/{category_id}',
    response_model=FoodCategoryResponseSchema,
    summary='Admin: update food category',
)
async def update_food_category(
    category_id: Annotated[
        str,
        Path(
            min_length=1,
            description='MongoDB food category id',
        ),
    ],
    data: FoodCategoryUpdateSchema,
    current_admin: Annotated[User, Depends(get_current_admin_user)],
    service: Annotated[FoodCategoryService, Depends(get_food_category_service)],
) -> FoodCategoryResponseSchema:
    return await service.update_category(
        category_id=category_id,
        data=data,
    )


@router.delete(
    '/categories/{category_id}',
    status_code=status.HTTP_200_OK,
    summary='Admin: deactivate food category',
)
async def deactivate_food_category(
    category_id: Annotated[
        str,
        Path(
            min_length=1,
            description='MongoDB food category id',
        ),
    ],
    current_admin: Annotated[User, Depends(get_current_admin_user)],
    service: Annotated[FoodCategoryService, Depends(get_food_category_service)],
) -> dict[str, str]:
    return await service.deactivate_category(category_id)
