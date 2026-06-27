from typing import Annotated

from fastapi import APIRouter, Depends, Path, status
from src.modules.auth.dependencies import JWTBearer
from src.modules.recipes.dependencies import get_recipe_service
from src.modules.recipes.schemas import (
    RecipeDetailResponseSchema,
    RecipeResponseSchema,
    RecipeSearchRequestSchema,
)
from src.modules.recipes.services import RecipeService

router = APIRouter()


@router.post(
    '/by-ingredients',
    response_model=list[RecipeResponseSchema],
    status_code=status.HTTP_200_OK,
    summary='Get recipe suggestions from inventory ingredients',
)
async def get_recipe_suggestions(
    data: RecipeSearchRequestSchema,
    jwt_data: Annotated[dict, Depends(JWTBearer())],
    service: Annotated[RecipeService, Depends(get_recipe_service)],
) -> list[RecipeResponseSchema]:
    return await service.get_recipes_by_inventory(
        data=data,
        user_id=jwt_data['sub'],
    )


@router.get(
    '/{spoonacular_id}',
    response_model=RecipeDetailResponseSchema,
    summary='Get recipe details with ingredient availability',
)
async def get_recipe_details(
    spoonacular_id: Annotated[
        int,
        Path(
            ge=1,
            description='Spoonacular recipe id',
        ),
    ],
    jwt_data: Annotated[dict, Depends(JWTBearer())],
    service: Annotated[RecipeService, Depends(get_recipe_service)],
) -> RecipeDetailResponseSchema:
    return await service.get_recipe_details(
        spoonacular_id=spoonacular_id,
        user_id=jwt_data['sub'],
    )
