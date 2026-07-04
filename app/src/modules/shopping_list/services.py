from datetime import UTC, datetime

from beanie import PydanticObjectId
from fastapi import HTTPException, status
from src.modules.categories.services import FoodCategoryService
from src.modules.shopping_list.models import ShoppingListItem
from src.modules.shopping_list.schemas import (
    ShoppingListItemCreateSchema,
    ShoppingListItemResponseSchema,
    ShoppingListItemUpdateSchema,
)


class ShoppingListService:
    def __init__(self):
        self.category_service = FoodCategoryService()

    async def _to_response(self, item: ShoppingListItem) -> ShoppingListItemResponseSchema:
        category = await self.category_service.get_category_document_by_id(
            category_id=str(item.category_id),
            active_only=False,
        )

        return ShoppingListItemResponseSchema(
            id=str(item.id),
            user_id=str(item.user_id),
            name=item.name,
            category=self.category_service._to_nested_response(category),
            amount=item.amount,
            unit=item.unit,
            is_checked=item.is_checked,
            source=item.source,
            source_id=item.source_id,
            added_at=item.added_at,
            updated_at=item.updated_at,
        )

    async def create_item(
        self,
        data: ShoppingListItemCreateSchema,
        user_id: str,
    ) -> ShoppingListItemResponseSchema:
        category = await self.category_service.get_category_document_by_id(
            category_id=data.category_id,
            active_only=True,
        )

        item = ShoppingListItem(
            user_id=PydanticObjectId(user_id),
            name=data.name,
            category_id=category.id,
            amount=data.amount,
            unit=data.unit,
            source=data.source,
            source_id=data.source_id,
        )

        await item.insert()
        return await self._to_response(item)

    async def get_items(
        self,
        user_id: str,
        include_checked: bool = True,
    ) -> list[ShoppingListItemResponseSchema]:
        filters = [
            ShoppingListItem.user_id == PydanticObjectId(user_id),
        ]

        if not include_checked:
            filters.append(ShoppingListItem.is_checked == False)  # noqa: E712

        items = await ShoppingListItem.find(*filters).sort(ShoppingListItem.added_at).to_list()

        return [await self._to_response(item) for item in items]

    async def get_item_by_id(
        self,
        item_id: str,
        user_id: str,
    ) -> ShoppingListItem:
        item = await ShoppingListItem.get(PydanticObjectId(item_id))

        if not item or item.user_id != PydanticObjectId(user_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Shopping list item not found',
            )

        return item

    async def update_item(
        self,
        item_id: str,
        user_id: str,
        data: ShoppingListItemUpdateSchema,
    ) -> ShoppingListItemResponseSchema:
        item = await self.get_item_by_id(
            item_id=item_id,
            user_id=user_id,
        )

        update_data = data.model_dump(exclude_unset=True)

        if 'category_id' in update_data:
            category = await self.category_service.get_category_document_by_id(
                category_id=update_data['category_id'],
                active_only=True,
            )
            update_data['category_id'] = category.id

        for field, value in update_data.items():
            setattr(item, field, value)

        item.updated_at = datetime.now(UTC)
        await item.save()

        return await self._to_response(item)

    async def toggle_checked(
        self,
        item_id: str,
        user_id: str,
    ) -> ShoppingListItemResponseSchema:
        item = await self.get_item_by_id(
            item_id=item_id,
            user_id=user_id,
        )

        item.is_checked = not item.is_checked
        item.updated_at = datetime.now(UTC)
        await item.save()

        return await self._to_response(item)

    async def delete_item(
        self,
        item_id: str,
        user_id: str,
    ) -> dict[str, str]:
        item = await self.get_item_by_id(
            item_id=item_id,
            user_id=user_id,
        )

        await item.delete()

        return {'detail': 'Shopping list item deleted'}

    async def clear_checked(
        self,
        user_id: str,
    ) -> dict[str, str]:
        items = await ShoppingListItem.find(
            ShoppingListItem.user_id == PydanticObjectId(user_id),
            ShoppingListItem.is_checked == True,  # noqa: E712
        ).to_list()

        deleted_count = 0

        for item in items:
            await item.delete()
            deleted_count += 1

        return {'detail': f'Deleted {deleted_count} checked shopping list items'}
