from typing import Annotated

from fastapi import APIRouter, Depends, Path, status
from src.modules.auth.dependencies import JWTBearer
from src.modules.products.dependencies import get_product_service
from src.modules.products.schemas import (
    ManualProductCreateSchema,
    ProductResponseSchema,
)
from src.modules.products.services import ProductService

router = APIRouter()


@router.get(
    '/barcode/{barcode}',
    response_model=ProductResponseSchema,
    summary='Get product by barcode',
)
async def get_product_by_barcode(
    barcode: Annotated[
        str,
        Path(
            min_length=1,
            max_length=50,
            pattern=r'^\S+$',
            description='Product barcode without spaces',
        ),
    ],
    _: Annotated[dict, Depends(JWTBearer())],
    service: Annotated[ProductService, Depends(get_product_service)],
) -> ProductResponseSchema:
    return await service.get_or_fetch_by_barcode(barcode)


@router.get(
    '/{product_id}',
    response_model=ProductResponseSchema,
    summary='Get product by id',
)
async def get_product_by_id(
    product_id: Annotated[
        str,
        Path(
            min_length=1,
            description='MongoDB product id',
        ),
    ],
    _: Annotated[dict, Depends(JWTBearer())],
    service: Annotated[ProductService, Depends(get_product_service)],
) -> ProductResponseSchema:
    return await service.get_product_by_id(product_id)


@router.post(
    '/manual',
    response_model=ProductResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary='Create product manually',
)
async def create_manual_product(
    data: ManualProductCreateSchema,
    _: Annotated[dict, Depends(JWTBearer())],
    service: Annotated[ProductService, Depends(get_product_service)],
) -> ProductResponseSchema:
    return await service.create_manual_product(data)
