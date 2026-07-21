# Programmer Name: Rakhmatullayeva Amina
# Program Name: FoodTrack
# Description: Builds scheduled expiration notification entries for inventory items.
# First Written on: Monday, 13-Jul-2026
# Edited on: Monday, 13-Jul-2026

from datetime import UTC, date, datetime, timedelta, timezone

from src.modules.inventory.models import ScheduledNotification

APP_TIMEZONE = timezone(timedelta(hours=8))


def build_scheduled_notifications(
    expiration_date: date,
    notification_days_before: list[int],
) -> list[ScheduledNotification]:
    local_now = datetime.now(APP_TIMEZONE)
    today = local_now.date()
    now = datetime.now(UTC)
    notifications: list[ScheduledNotification] = []

    for days_before in notification_days_before:
        scheduled_date = expiration_date - timedelta(days=days_before)

        if scheduled_date < today:
            continue

        scheduled_for_local = datetime.combine(
            scheduled_date,
            datetime.min.time(),
            tzinfo=APP_TIMEZONE,
        )

        scheduled_for = scheduled_for_local.astimezone(UTC)
        scheduled_for = max(now, scheduled_for)

        notifications.append(
            ScheduledNotification(
                days_before=days_before,
                scheduled_for=scheduled_for,
            )
        )

    return notifications
