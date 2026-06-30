from beanie import PydanticObjectId
from fastapi import HTTPException, status
from src.modules.categories.models import FoodCategory
from src.modules.categories.schemas import FoodCategoryResponseSchema


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
