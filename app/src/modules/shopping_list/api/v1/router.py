# Programmer Name: Rakhmatullayeva Amina
# Program Name: FoodTrack
# Description: API endpoints for managing the user's shopping list.
# First Written on: Tuesday, 23-Jun-2026
# Edited on: Tuesday, 23-Jun-2026

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status
from src.modules.auth.dependencies import JWTBearer
from src.modules.shopping_list.dependencies import get_shopping_list_service
from src.modules.shopping_list.schemas import (
    ShoppingListItemCreateSchema,
    ShoppingListItemResponseSchema,
    ShoppingListItemUpdateSchema,
)
from src.modules.shopping_list.services import ShoppingListService

router = APIRouter()


@router.post(
    '',
    response_model=ShoppingListItemResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary='Create shopping list item',
)
async def create_shopping_list_item(
    data: ShoppingListItemCreateSchema,
    jwt_data: Annotated[dict, Depends(JWTBearer())],
    service: Annotated[ShoppingListService, Depends(get_shopping_list_service)],
) -> ShoppingListItemResponseSchema:
    return await service.create_item(
        data=data,
        user_id=jwt_data['sub'],
    )


@router.get(
    '',
    response_model=list[ShoppingListItemResponseSchema],
    summary='Get shopping list items',
)
async def get_shopping_list_items(
    jwt_data: Annotated[dict, Depends(JWTBearer())],
    service: Annotated[ShoppingListService, Depends(get_shopping_list_service)],
    include_checked: Annotated[bool, Query()] = True,
) -> list[ShoppingListItemResponseSchema]:
    return await service.get_items(
        user_id=jwt_data['sub'],
        include_checked=include_checked,
    )


@router.patch(
    '/{item_id}',
    response_model=ShoppingListItemResponseSchema,
    summary='Update shopping list item',
)
async def update_shopping_list_item(
    item_id: Annotated[
        str,
        Path(
            min_length=1,
            description='MongoDB shopping list item id',
        ),
    ],
    data: ShoppingListItemUpdateSchema,
    jwt_data: Annotated[dict, Depends(JWTBearer())],
    service: Annotated[ShoppingListService, Depends(get_shopping_list_service)],
) -> ShoppingListItemResponseSchema:
    return await service.update_item(
        item_id=item_id,
        user_id=jwt_data['sub'],
        data=data,
    )


@router.patch(
    '/{item_id}/check',
    response_model=ShoppingListItemResponseSchema,
    summary='Toggle shopping list item checked state',
)
async def toggle_shopping_list_item_checked(
    item_id: Annotated[
        str,
        Path(
            min_length=1,
            description='MongoDB shopping list item id',
        ),
    ],
    jwt_data: Annotated[dict, Depends(JWTBearer())],
    service: Annotated[ShoppingListService, Depends(get_shopping_list_service)],
) -> ShoppingListItemResponseSchema:
    return await service.toggle_checked(
        item_id=item_id,
        user_id=jwt_data['sub'],
    )


@router.delete(
    '/checked',
    status_code=status.HTTP_200_OK,
    summary='Clear checked shopping list items',
)
async def clear_checked_shopping_list_items(
    jwt_data: Annotated[dict, Depends(JWTBearer())],
    service: Annotated[ShoppingListService, Depends(get_shopping_list_service)],
) -> dict[str, str]:
    return await service.clear_checked(
        user_id=jwt_data['sub'],
    )


@router.delete(
    '/{item_id}',
    status_code=status.HTTP_200_OK,
    summary='Delete shopping list item',
)
async def delete_shopping_list_item(
    item_id: Annotated[
        str,
        Path(
            min_length=1,
            description='MongoDB shopping list item id',
        ),
    ],
    jwt_data: Annotated[dict, Depends(JWTBearer())],
    service: Annotated[ShoppingListService, Depends(get_shopping_list_service)],
) -> dict[str, str]:
    return await service.delete_item(
        item_id=item_id,
        user_id=jwt_data['sub'],
    )
