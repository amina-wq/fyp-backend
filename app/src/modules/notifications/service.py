import logging
from datetime import UTC, datetime

from beanie import PydanticObjectId
from src.core.firebase import FirebaseService
from src.modules.auth.models import User
from src.modules.inventory.models import InventoryItem, InventoryStatus, ScheduledNotification
from src.modules.products.models import Product

logger = logging.getLogger(__name__)


class NotificationService:
    async def send_test_notification(self, user: User) -> bool:
        if not user.fcm_token:
            return False

        return await FirebaseService.send_push_notification(
            token=user.fcm_token,
            title='Test notification',
            body='This is a test push notification. If you can see this, push delivery is working.',
            data={'type': 'test'},
        )

    async def process_due_notifications(self) -> dict[str, int]:
        now = datetime.now(UTC)

        processed_count = 0
        sent_count = 0
        skipped_count = 0
        failed_count = 0

        items = await InventoryItem.find(
            InventoryItem.status == InventoryStatus.ACTIVE,
        ).to_list()

        users_by_id: dict[PydanticObjectId, User | None] = {}

        for item in items:
            due_notifications = self._get_due_notifications(
                notifications=item.scheduled_notifications,
                now=now,
            )

            if not due_notifications:
                continue

            processed_count += len(due_notifications)

            if item.user_id not in users_by_id:
                users_by_id[item.user_id] = await User.get(item.user_id)

            user = users_by_id[item.user_id]

            if not user:
                skipped_count += len(due_notifications)
                self._mark_notifications_as_sent(due_notifications, now)
                item.updated_at = now
                await item.save()
                logger.warning(
                    'Notification skipped because user was not found: item_id=%s user_id=%s notification_count=%s',
                    item.id,
                    item.user_id,
                    len(due_notifications),
                )
                continue

            if not user.expiry_notifications_enabled:
                skipped_count += len(due_notifications)
                self._mark_notifications_as_sent(due_notifications, now)
                item.updated_at = now
                await item.save()
                logger.info(
                    'Notification skipped because notifications are disabled: '
                    'item_id=%s user_id=%s notification_count=%s',
                    item.id,
                    user.id,
                    len(due_notifications),
                )
                continue

            product_name = await self._get_item_display_name(item)

            for notification in due_notifications:
                if not user.fcm_token:
                    skipped_count += 1
                    notification.is_sent = True
                    notification.sent_at = now
                    item.updated_at = now
                    await item.save()
                    logger.info(
                        'Notification skipped because FCM token is missing: item_id=%s user_id=%s days_before=%s',
                        item.id,
                        user.id,
                        notification.days_before,
                    )
                    continue

                is_sent = await FirebaseService.send_push_notification(
                    token=user.fcm_token,
                    title=self._build_notification_title(notification.days_before),
                    body=self._build_notification_body(
                        product_name=product_name,
                        days_before=notification.days_before,
                    ),
                    data={
                        'type': 'expiry_warning',
                        'item_id': str(item.id),
                        'days_before': str(notification.days_before),
                    },
                )

                if is_sent:
                    sent_count += 1
                    notification.is_sent = True
                    notification.sent_at = now
                    item.updated_at = now
                    await item.save()
                    logger.info(
                        'Notification sent: item_id=%s user_id=%s days_before=%s',
                        item.id,
                        user.id,
                        notification.days_before,
                    )
                else:
                    failed_count += 1
                    logger.warning(
                        'Notification failed: item_id=%s user_id=%s days_before=%s',
                        item.id,
                        user.id,
                        notification.days_before,
                    )

        if processed_count:
            logger.info(
                'Processed due notifications: processed=%s sent=%s skipped=%s failed=%s',
                processed_count,
                sent_count,
                skipped_count,
                failed_count,
            )

        return {
            'processed': processed_count,
            'sent': sent_count,
            'skipped': skipped_count,
            'failed': failed_count,
        }

    def _get_due_notifications(
        self,
        notifications: list[ScheduledNotification],
        now: datetime,
    ) -> list[ScheduledNotification]:
        due_notifications: list[ScheduledNotification] = []

        for notification in notifications:
            scheduled_for = notification.scheduled_for

            if scheduled_for.tzinfo is None:
                scheduled_for = scheduled_for.replace(tzinfo=UTC)

            if not notification.is_sent and scheduled_for <= now:
                due_notifications.append(notification)

        return due_notifications

    def _mark_notifications_as_sent(
        self,
        notifications: list[ScheduledNotification],
        sent_at: datetime,
    ) -> None:
        for notification in notifications:
            notification.is_sent = True
            notification.sent_at = sent_at

    async def _get_item_display_name(self, item: InventoryItem) -> str:
        if item.custom_name:
            return item.custom_name

        if item.product_id:
            product = await Product.get(item.product_id)

            if product:
                return product.name

        return 'Your food item'

    def _build_notification_title(self, days_before: int) -> str:
        if days_before == 0:
            return 'Food expires today'

        if days_before == 1:
            return 'Food expires tomorrow'

        return f'Food expires in {days_before} days'

    def _build_notification_body(
        self,
        product_name: str,
        days_before: int,
    ) -> str:
        if days_before == 0:
            return f'{product_name} expires today. Check it before it goes to waste.'

        if days_before == 1:
            return f'{product_name} expires tomorrow. Plan to use it soon.'

        return f'{product_name} expires in {days_before} days. Plan ahead to avoid waste.'
