from datetime import UTC, date, datetime, timedelta

from beanie import PydanticObjectId
from fastapi import HTTPException, status
from src.core.enums import FoodCategory
from src.modules.auth.models import User
from src.modules.inventory.models import InventoryItem, InventoryStatus, ScheduledNotification
from src.modules.inventory.schemas import (
    ExpiryState,
    InventoryItemCreateSchema,
    InventoryItemResponseSchema,
    InventoryItemUpdateSchema,
    InventoryStatsResponseSchema,
)
from src.modules.products.models import Product
from src.modules.products.services import ProductService


class InventoryService:
    def __init__(self):
        self.product_service = ProductService()

    def _calculate_expiry_state(self, expiration_date: date) -> ExpiryState:
        today = date.today()

        if expiration_date < today:
            return ExpiryState.EXPIRED

        if expiration_date <= today + timedelta(days=3):
            return ExpiryState.EXPIRING

        return ExpiryState.FRESH

    def _build_scheduled_notifications(
        self,
        expiration_date: date,
        notification_days_before: list[int],
    ) -> list[ScheduledNotification]:
        now = datetime.now(UTC)
        notifications: list[ScheduledNotification] = []

        for days_before in notification_days_before:
            scheduled_date = expiration_date - timedelta(days=days_before)
            scheduled_for = datetime.combine(
                scheduled_date,
                datetime.min.time(),
                tzinfo=UTC,
            )

            if scheduled_for > now:
                notifications.append(
                    ScheduledNotification(
                        days_before=days_before,
                        scheduled_for=scheduled_for,
                    )
                )

        return notifications

    async def _get_user_item_or_404(
        self,
        item_id: str,
        user_id: str,
    ) -> InventoryItem:
        try:
            item_object_id = PydanticObjectId(item_id)
            user_object_id = PydanticObjectId(user_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Invalid item id or user id',
            )

        item = await InventoryItem.find_one(
            InventoryItem.id == item_object_id,
            InventoryItem.user_id == user_object_id,
            InventoryItem.status != InventoryStatus.DELETED,
        )

        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Inventory item not found',
            )

        return item

    async def _get_product_display_name(
        self,
        item: InventoryItem,
    ) -> str:
        if item.custom_name:
            return item.custom_name

        if item.product_id:
            product = await Product.get(item.product_id)

            if product:
                return product.name

        return 'Unnamed product'

    async def _to_response(self, item: InventoryItem) -> InventoryItemResponseSchema:
        display_name = await self._get_product_display_name(item)
        expiry_state = self._calculate_expiry_state(item.expiration_date)

        return InventoryItemResponseSchema(
            id=str(item.id),
            user_id=str(item.user_id),
            product_id=str(item.product_id) if item.product_id else None,
            barcode=item.barcode,
            custom_name=item.custom_name,
            display_name=display_name,
            category=item.category,
            notes=item.notes,
            location=item.location,
            amount=item.amount,
            unit=item.unit,
            expiration_date=item.expiration_date,
            status=item.status,
            expiry_state=expiry_state,
            scheduled_notifications=item.scheduled_notifications,
            added_at=item.added_at,
            updated_at=item.updated_at,
        )

    async def _change_status(
        self,
        item_id: str,
        user_id: str,
        new_status: InventoryStatus,
    ) -> InventoryItem:
        item = await self._get_user_item_or_404(
            item_id=item_id,
            user_id=user_id,
        )

        item.status = new_status
        item.updated_at = datetime.now(UTC)

        for notification in item.scheduled_notifications:
            if not notification.is_sent:
                notification.is_sent = True
                notification.sent_at = datetime.now(UTC)

        await item.save()

        return item

    async def create_item(
        self,
        data: InventoryItemCreateSchema,
        user_id: str,
    ) -> InventoryItemResponseSchema:
        try:
            user_object_id = PydanticObjectId(user_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Invalid user id',
            )

        user = await User.get(user_object_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='User not found',
            )

        product_object_id: PydanticObjectId | None = None
        barcode: str | None = data.barcode

        if data.product_id:
            try:
                product_object_id = PydanticObjectId(data.product_id)
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail='Invalid product id',
                )

            product = await Product.get(product_object_id)

            if not product:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail='Product not found',
                )

            if data.barcode and product.barcode and data.barcode != product.barcode:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail='Product id and barcode do not match',
                )

            barcode = product.barcode

        elif data.barcode:
            product_response = await self.product_service.get_or_fetch_by_barcode(data.barcode)

            product_object_id = PydanticObjectId(product_response.id)
            barcode = product_response.barcode

        scheduled_notifications = self._build_scheduled_notifications(
            expiration_date=data.expiration_date,
            notification_days_before=user.notification_days_before,
        )

        item = InventoryItem(
            user_id=user_object_id,
            product_id=product_object_id,
            barcode=barcode,
            custom_name=data.custom_name,
            category=data.category,
            notes=data.notes,
            location=data.location,
            amount=data.amount,
            unit=data.unit,
            expiration_date=data.expiration_date,
            status=InventoryStatus.ACTIVE,
            scheduled_notifications=scheduled_notifications,
        )

        await item.insert()

        return await self._to_response(item)

    async def get_items(
        self,
        user_id: str,
        category: FoodCategory | None = None,
        expiry_state: ExpiryState | None = None,
    ) -> list[InventoryItemResponseSchema]:
        try:
            user_object_id = PydanticObjectId(user_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Invalid user id',
            )

        query = [
            InventoryItem.user_id == user_object_id,
            InventoryItem.status == InventoryStatus.ACTIVE,
        ]

        if category:
            query.append(InventoryItem.category == category)

        items = await InventoryItem.find(*query).sort('-added_at').to_list()

        response_items: list[InventoryItemResponseSchema] = []

        for item in items:
            response_item = await self._to_response(item)

            if expiry_state and response_item.expiry_state != expiry_state:
                continue

            response_items.append(response_item)

        return response_items

    async def get_item_by_id(
        self,
        item_id: str,
        user_id: str,
    ) -> InventoryItemResponseSchema:
        item = await self._get_user_item_or_404(
            item_id=item_id,
            user_id=user_id,
        )

        return await self._to_response(item)

    async def update_item(
        self,
        item_id: str,
        user_id: str,
        data: InventoryItemUpdateSchema,
    ) -> InventoryItemResponseSchema:
        item = await self._get_user_item_or_404(
            item_id=item_id,
            user_id=user_id,
        )

        update_data = data.model_dump(exclude_none=True)

        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Nothing to update',
            )

        for field_name, field_value in update_data.items():
            setattr(item, field_name, field_value)

        if 'expiration_date' in update_data:
            user = await User.get(item.user_id)

            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail='User not found',
                )

            item.scheduled_notifications = self._build_scheduled_notifications(
                expiration_date=item.expiration_date,
                notification_days_before=user.notification_days_before,
            )

        item.updated_at = datetime.now(UTC)

        await item.save()

        return await self._to_response(item)

    async def consume_item(
        self,
        item_id: str,
        user_id: str,
    ) -> InventoryItemResponseSchema:
        item = await self._change_status(
            item_id=item_id,
            user_id=user_id,
            new_status=InventoryStatus.CONSUMED,
        )

        return await self._to_response(item)

    async def waste_item(
        self,
        item_id: str,
        user_id: str,
    ) -> InventoryItemResponseSchema:
        item = await self._change_status(
            item_id=item_id,
            user_id=user_id,
            new_status=InventoryStatus.WASTED,
        )

        return await self._to_response(item)

    async def delete_item(
        self,
        item_id: str,
        user_id: str,
    ) -> dict[str, str]:
        await self._change_status(
            item_id=item_id,
            user_id=user_id,
            new_status=InventoryStatus.DELETED,
        )

        return {'detail': 'Inventory item deleted'}

    async def get_stats(
        self,
        user_id: str,
    ) -> InventoryStatsResponseSchema:
        try:
            user_object_id = PydanticObjectId(user_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Invalid user id',
            )

        today = date.today()
        tomorrow = today + timedelta(days=1)
        in_5_days = today + timedelta(days=5)

        expired_count = 0
        expiring_tomorrow_count = 0
        expiring_in_5_days_count = 0
        fresh_count = 0

        items = await InventoryItem.find(
            InventoryItem.user_id == user_object_id,
            InventoryItem.status == InventoryStatus.ACTIVE,
        ).to_list()

        for item in items:
            if item.expiration_date < today:
                expired_count += 1

            elif item.expiration_date == tomorrow:
                expiring_tomorrow_count += 1

            elif item.expiration_date <= in_5_days:
                expiring_in_5_days_count += 1

            else:
                fresh_count += 1

        return InventoryStatsResponseSchema(
            expired_count=expired_count,
            expiring_tomorrow_count=expiring_tomorrow_count,
            expiring_in_5_days_count=expiring_in_5_days_count,
            fresh_count=fresh_count,
        )
