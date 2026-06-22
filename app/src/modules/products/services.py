from datetime import UTC, datetime

from beanie import PydanticObjectId
from fastapi import HTTPException, status
from pymongo.errors import DuplicateKeyError
from src.modules.products.models import Product, ProductSource
from src.modules.products.off_client import fetch_product_by_barcode
from src.modules.products.schemas import (
    ManualProductCreateSchema,
    ProductResponseSchema,
)


class ProductService:
    def _to_response(self, product: Product) -> ProductResponseSchema:
        return ProductResponseSchema(
            id=str(product.id),
            barcode=product.barcode,
            name=product.name,
            brand=product.brand,
            tags=product.tags,
            image_url=product.image_url,
            quantity=product.quantity,
            source=product.source,
            is_verified=product.is_verified,
            created_at=product.created_at,
            updated_at=product.updated_at,
        )

    async def get_product_by_id(self, product_id: str) -> ProductResponseSchema:
        try:
            object_id = PydanticObjectId(product_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Invalid product id',
            )

        product = await Product.get(object_id)

        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Product not found',
            )

        return self._to_response(product)

    async def get_or_fetch_by_barcode(self, barcode: str) -> ProductResponseSchema:
        barcode = barcode.strip()

        if not barcode:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Barcode cannot be empty',
            )

        if ' ' in barcode:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Barcode cannot contain spaces',
            )

        existing_product = await Product.find_one(Product.barcode == barcode)

        if existing_product:
            if not existing_product.image_url:
                off_product = await fetch_product_by_barcode(barcode)

                if off_product and off_product.get('image_url'):
                    existing_product.image_url = off_product.get('image_url')
                    existing_product.updated_at = datetime.now(UTC)
                    await existing_product.save()

            return self._to_response(existing_product)

        off_product = await fetch_product_by_barcode(barcode)

        if not off_product or not off_product.get('name'):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Product not found. Try adding it manually',
            )

        product = Product(
            barcode=off_product.get('barcode'),
            name=off_product['name'],
            brand=off_product.get('brand'),
            tags=off_product.get('tags', []),
            image_url=off_product.get('image_url'),
            quantity=off_product.get('quantity'),
            source=ProductSource.OPEN_FOOD_FACTS,
            is_verified=True,
        )

        try:
            await product.insert()
        except DuplicateKeyError:
            existing_product = await Product.find_one(Product.barcode == barcode)

            if existing_product:
                return self._to_response(existing_product)

            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail='Product with this barcode already exists',
            )

        return self._to_response(product)

    async def create_manual_product(
        self,
        data: ManualProductCreateSchema,
    ) -> ProductResponseSchema:
        if not data.barcode:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Manual product must have a barcode. '
                'Custom food without barcode should be added directly to inventory.',
            )

        existing_product = await Product.find_one(Product.barcode == data.barcode)

        if existing_product:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail='Product with this barcode already exists',
            )

        product = Product(
            barcode=data.barcode,
            name=data.name,
            brand=data.brand,
            tags=data.tags,
            image_url=data.image_url,
            quantity=data.quantity,
            source=ProductSource.MANUAL,
            is_verified=False,
            updated_at=datetime.now(UTC),
        )

        try:
            await product.insert()
        except DuplicateKeyError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail='Product with this barcode already exists',
            )

        return self._to_response(product)
