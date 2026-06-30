from typing import Annotated

from fastapi import APIRouter, Depends, Path
from src.modules.categories.dependencies import get_food_category_service
from src.modules.categories.schemas import FoodCategoryResponseSchema
from src.modules.categories.services import FoodCategoryService

router = APIRouter()


@router.get(
    '',
    response_model=list[FoodCategoryResponseSchema],
    summary='Get active food categories',
)
async def get_food_categories(
    service: Annotated[FoodCategoryService, Depends(get_food_category_service)],
) -> list[FoodCategoryResponseSchema]:
    return await service.get_active_categories()


@router.get(
    '/{category_id}',
    response_model=FoodCategoryResponseSchema,
    summary='Get food category by id',
)
async def get_food_category_by_id(
    category_id: Annotated[
        str,
        Path(
            min_length=1,
            description='MongoDB food category id',
        ),
    ],
    service: Annotated[FoodCategoryService, Depends(get_food_category_service)],
) -> FoodCategoryResponseSchema:
    return await service.get_category_by_id(category_id)
