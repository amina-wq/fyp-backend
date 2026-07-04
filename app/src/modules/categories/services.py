import uuid
from datetime import UTC, datetime
from urllib.parse import urlparse

import boto3
from beanie import PydanticObjectId
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import HTTPException, UploadFile, status
from src.core.config import settings
from src.modules.categories.models import FoodCategory
from src.modules.categories.schemas import (
    FoodCategoryCreateSchema,
    FoodCategoryNestedSchema,
    FoodCategoryResponseSchema,
    FoodCategoryUpdateSchema,
)

ALLOWED_ICON_TYPES = {
    'image/jpeg': '.jpg',
    'image/png': '.png',
    'image/webp': '.webp',
}

MAX_ICON_SIZE = 2 * 1024 * 1024

S3_CATEGORY_ICONS_PREFIX = 'category_icons'


class FoodCategoryService:
    def __init__(self):
        s3_client_kwargs = {
            'region_name': settings.AWS_REGION,
        }

        if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
            s3_client_kwargs['aws_access_key_id'] = settings.AWS_ACCESS_KEY_ID
            s3_client_kwargs['aws_secret_access_key'] = settings.AWS_SECRET_ACCESS_KEY

        self.s3_client = boto3.client(
            's3',
            **s3_client_kwargs,
        )

    def _build_s3_icon_key(
        self,
        category_id: str,
        extension: str,
    ) -> str:
        return f'{S3_CATEGORY_ICONS_PREFIX}/{category_id}_{uuid.uuid4().hex}{extension}'

    def _build_s3_public_url(self, object_key: str) -> str:
        base_url = settings.AWS_S3_PUBLIC_BASE_URL.rstrip('/')

        return f'{base_url}/{object_key}'

    def _extract_s3_key_from_url(self, icon_url: str | None) -> str | None:
        if not icon_url:
            return None

        base_url = settings.AWS_S3_PUBLIC_BASE_URL.rstrip('/')

        if not icon_url.startswith(base_url):
            return None

        parsed_url = urlparse(icon_url)
        object_key = parsed_url.path.lstrip('/')

        if not object_key.startswith(f'{S3_CATEGORY_ICONS_PREFIX}/'):
            return None

        return object_key

    def _delete_s3_icon_if_exists(self, icon_url: str | None) -> None:
        object_key = self._extract_s3_key_from_url(icon_url)

        if object_key is None:
            return

        try:
            self.s3_client.delete_object(
                Bucket=settings.AWS_S3_BUCKET_NAME,
                Key=object_key,
            )
        except (BotoCoreError, ClientError):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Failed to delete old category icon from S3',
            )

    async def upload_category_icon(
        self,
        category_id: str,
        icon: UploadFile,
    ) -> FoodCategoryResponseSchema:
        try:
            category_object_id = PydanticObjectId(category_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Invalid category id',
            )

        category = await FoodCategory.get(category_object_id)

        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Category not found',
            )

        content_type = icon.content_type

        if content_type is None or content_type not in ALLOWED_ICON_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Only JPEG, PNG and WEBP icons are allowed',
            )

        content = await icon.read()

        if len(content) > MAX_ICON_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Icon size must be less than 2MB',
            )

        extension = ALLOWED_ICON_TYPES[content_type]
        object_key = self._build_s3_icon_key(
            category_id=str(category.id),
            extension=extension,
        )

        try:
            self.s3_client.put_object(
                Bucket=settings.AWS_S3_BUCKET_NAME,
                Key=object_key,
                Body=content,
                ContentType=content_type,
            )
        except (BotoCoreError, ClientError) as error:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f'Failed to upload category icon to S3: {error}',
            )

        self._delete_s3_icon_if_exists(category.icon_url)

        category.icon_url = self._build_s3_public_url(object_key)
        category.updated_at = datetime.now(UTC)

        await category.save()

        return self._to_response(category)

    def _to_response(
        self,
        category: FoodCategory,
    ) -> FoodCategoryResponseSchema:
        return FoodCategoryResponseSchema(
            id=str(category.id),
            key=category.key,
            name=category.name,
            description=category.description,
            icon_url=category.icon_url,
            color_hex=category.color_hex,
            is_active=category.is_active,
            is_default=category.is_default,
            sort_order=category.sort_order,
            created_at=category.created_at,
            updated_at=category.updated_at,
        )

    async def get_active_categories(self) -> list[FoodCategoryResponseSchema]:
        categories = (
            await FoodCategory.find(
                FoodCategory.is_active == True,  # noqa: E712
            )
            .sort(FoodCategory.sort_order)
            .to_list()
        )

        return [self._to_response(category) for category in categories]

    async def get_category_by_id(
        self,
        category_id: str,
    ) -> FoodCategoryResponseSchema:
        try:
            category_object_id = PydanticObjectId(category_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Invalid category id',
            )

        category = await FoodCategory.get(category_object_id)

        if not category or not category.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Category not found',
            )

        return self._to_response(category)

    async def get_all_categories_for_admin(self) -> list[FoodCategoryResponseSchema]:
        categories = await FoodCategory.find_all().sort(FoodCategory.sort_order).to_list()

        return [self._to_response(category) for category in categories]

    async def create_category(
        self,
        data: FoodCategoryCreateSchema,
    ) -> FoodCategoryResponseSchema:
        key = data.key.strip().lower().replace(' ', '_')

        existing_category = await FoodCategory.find_one(
            FoodCategory.key == key,
        )

        if existing_category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Category with this key already exists',
            )

        category = FoodCategory(
            key=key,
            name=data.name.strip(),
            description=data.description,
            icon_url=data.icon_url,
            color_hex=data.color_hex,
            is_active=True,
            is_default=False,
            sort_order=data.sort_order,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        await category.insert()

        return self._to_response(category)

    async def update_category(
        self,
        category_id: str,
        data: FoodCategoryUpdateSchema,
    ) -> FoodCategoryResponseSchema:
        try:
            category_object_id = PydanticObjectId(category_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Invalid category id',
            )

        category = await FoodCategory.get(category_object_id)

        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Category not found',
            )

        update_data = data.model_dump(exclude_unset=True)

        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Nothing to update',
            )

        for field_name, field_value in update_data.items():
            cleaned_value = field_value

            if field_name == 'name' and isinstance(field_value, str):
                cleaned_value = field_value.strip()

            setattr(category, field_name, cleaned_value)

        category.updated_at = datetime.now(UTC)

        await category.save()

        return self._to_response(category)

    async def deactivate_category(
        self,
        category_id: str,
    ) -> dict[str, str]:
        try:
            category_object_id = PydanticObjectId(category_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Invalid category id',
            )

        category = await FoodCategory.get(category_object_id)

        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Category not found',
            )

        category.is_active = False
        category.updated_at = datetime.now(UTC)

        await category.save()

        return {'detail': 'Category deactivated'}

    def _to_nested_response(
        self,
        category: FoodCategory,
    ) -> FoodCategoryNestedSchema:
        return FoodCategoryNestedSchema(
            id=str(category.id),
            key=category.key,
            name=category.name,
            description=category.description,
            icon_url=category.icon_url,
            color_hex=category.color_hex,
            is_active=category.is_active,
            is_default=category.is_default,
            sort_order=category.sort_order,
        )

    async def get_category_document_by_id(
        self,
        category_id: str,
        active_only: bool = True,
    ) -> FoodCategory:
        try:
            category_object_id = PydanticObjectId(category_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Invalid category id',
            )

        category = await FoodCategory.get(category_object_id)

        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Category not found',
            )

        if active_only and not category.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Category is inactive',
            )

        return category
