from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status
from src.core.enums import FoodCategory
from src.modules.auth.dependencies import JWTBearer
from src.modules.inventory.dependencies import get_inventory_service
from src.modules.inventory.schemas import (
    ExpiryState,
    InventoryItemCreateSchema,
    InventoryItemResponseSchema,
    InventoryItemUpdateSchema,
    InventoryStatsResponseSchema,
)
from src.modules.inventory.services import InventoryService

router = APIRouter()


@router.post(
    '',
    response_model=InventoryItemResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary='Create inventory item',
)
async def create_inventory_item(
    data: InventoryItemCreateSchema,
    jwt_data: Annotated[dict, Depends(JWTBearer())],
    service: Annotated[InventoryService, Depends(get_inventory_service)],
) -> InventoryItemResponseSchema:
    return await service.create_item(
        data=data,
        user_id=jwt_data['sub'],
    )


@router.get(
    '',
    response_model=list[InventoryItemResponseSchema],
    summary='Get inventory items',
)
async def get_inventory_items(
    jwt_data: Annotated[dict, Depends(JWTBearer())],
    service: Annotated[InventoryService, Depends(get_inventory_service)],
    category: Annotated[FoodCategory | None, Query()] = None,
    expiry_state: Annotated[ExpiryState | None, Query()] = None,
) -> list[InventoryItemResponseSchema]:
    return await service.get_items(
        user_id=jwt_data['sub'],
        category=category,
        expiry_state=expiry_state,
    )


@router.get(
    '/stats',
    response_model=InventoryStatsResponseSchema,
    summary='Get inventory stats',
)
async def get_inventory_stats(
    jwt_data: Annotated[dict, Depends(JWTBearer())],
    service: Annotated[InventoryService, Depends(get_inventory_service)],
) -> InventoryStatsResponseSchema:
    return await service.get_stats(
        user_id=jwt_data['sub'],
    )


@router.get(
    '/{item_id}',
    response_model=InventoryItemResponseSchema,
    summary='Get inventory item by id',
)
async def get_inventory_item_by_id(
    item_id: Annotated[
        str,
        Path(
            min_length=1,
            description='MongoDB inventory item id',
        ),
    ],
    jwt_data: Annotated[dict, Depends(JWTBearer())],
    service: Annotated[InventoryService, Depends(get_inventory_service)],
) -> InventoryItemResponseSchema:
    return await service.get_item_by_id(
        item_id=item_id,
        user_id=jwt_data['sub'],
    )


@router.patch(
    '/{item_id}',
    response_model=InventoryItemResponseSchema,
    summary='Update inventory item',
)
async def update_inventory_item(
    item_id: Annotated[
        str,
        Path(
            min_length=1,
            description='MongoDB inventory item id',
        ),
    ],
    data: InventoryItemUpdateSchema,
    jwt_data: Annotated[dict, Depends(JWTBearer())],
    service: Annotated[InventoryService, Depends(get_inventory_service)],
) -> InventoryItemResponseSchema:
    return await service.update_item(
        item_id=item_id,
        user_id=jwt_data['sub'],
        data=data,
    )


@router.patch(
    '/{item_id}/consume',
    response_model=InventoryItemResponseSchema,
    summary='Mark inventory item as consumed',
)
async def consume_inventory_item(
    item_id: Annotated[
        str,
        Path(
            min_length=1,
            description='MongoDB inventory item id',
        ),
    ],
    jwt_data: Annotated[dict, Depends(JWTBearer())],
    service: Annotated[InventoryService, Depends(get_inventory_service)],
) -> InventoryItemResponseSchema:
    return await service.consume_item(
        item_id=item_id,
        user_id=jwt_data['sub'],
    )


@router.patch(
    '/{item_id}/waste',
    response_model=InventoryItemResponseSchema,
    summary='Mark inventory item as wasted',
)
async def waste_inventory_item(
    item_id: Annotated[
        str,
        Path(
            min_length=1,
            description='MongoDB inventory item id',
        ),
    ],
    jwt_data: Annotated[dict, Depends(JWTBearer())],
    service: Annotated[InventoryService, Depends(get_inventory_service)],
) -> InventoryItemResponseSchema:
    return await service.waste_item(
        item_id=item_id,
        user_id=jwt_data['sub'],
    )


@router.delete(
    '/{item_id}',
    status_code=status.HTTP_200_OK,
    summary='Delete inventory item',
)
async def delete_inventory_item(
    item_id: Annotated[
        str,
        Path(
            min_length=1,
            description='MongoDB inventory item id',
        ),
    ],
    jwt_data: Annotated[dict, Depends(JWTBearer())],
    service: Annotated[InventoryService, Depends(get_inventory_service)],
) -> dict[str, str]:
    return await service.delete_item(
        item_id=item_id,
        user_id=jwt_data['sub'],
    )
