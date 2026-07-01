from datetime import UTC, datetime

from beanie import PydanticObjectId
from fastapi import HTTPException, status
from src.modules.categories.models import FoodCategory
from src.modules.categories.schemas import (
    FoodCategoryCreateSchema,
    FoodCategoryResponseSchema,
    FoodCategoryUpdateSchema,
)


class FoodCategoryService:
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
