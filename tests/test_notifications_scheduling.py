from datetime import UTC, datetime, timedelta

from src.modules.notifications.scheduling import APP_TIMEZONE, build_scheduled_notifications


def _today():
    return datetime.now(APP_TIMEZONE).date()


def test_build_scheduled_notifications_keeps_future_days_in_order() -> None:
    expiration_date = _today() + timedelta(days=10)

    notifications = build_scheduled_notifications(
        expiration_date=expiration_date,
        notification_days_before=[7, 3, 1],
    )

    assert [n.days_before for n in notifications] == [7, 3, 1]


def test_build_scheduled_notifications_skips_past_days() -> None:
    expiration_date = _today() + timedelta(days=1)

    notifications = build_scheduled_notifications(
        expiration_date=expiration_date,
        notification_days_before=[5, 1, 0],
    )

    assert [n.days_before for n in notifications] == [1, 0]


def test_build_scheduled_notifications_empty_input_returns_empty() -> None:
    notifications = build_scheduled_notifications(
        expiration_date=_today() + timedelta(days=5),
        notification_days_before=[],
    )

    assert notifications == []


def test_build_scheduled_notifications_all_past_returns_empty() -> None:
    expiration_date = _today() - timedelta(days=20)

    notifications = build_scheduled_notifications(
        expiration_date=expiration_date,
        notification_days_before=[5, 1, 0],
    )

    assert notifications == []


def test_build_scheduled_notifications_clamps_same_day_to_now() -> None:
    expiration_date = _today()

    notifications = build_scheduled_notifications(
        expiration_date=expiration_date,
        notification_days_before=[0],
    )

    assert len(notifications) == 1

    now = datetime.now(UTC)

    assert notifications[0].scheduled_for <= now
    assert (now - notifications[0].scheduled_for) < timedelta(seconds=10)


def test_build_scheduled_notifications_future_day_is_not_clamped_to_now() -> None:
    expiration_date = _today() + timedelta(days=30)

    notifications = build_scheduled_notifications(
        expiration_date=expiration_date,
        notification_days_before=[7],
    )

    assert len(notifications) == 1

    now = datetime.now(UTC)

    assert notifications[0].scheduled_for > now + timedelta(days=20)


def test_build_scheduled_notifications_scheduled_for_is_timezone_aware_utc() -> None:
    expiration_date = _today() + timedelta(days=5)

    notifications = build_scheduled_notifications(
        expiration_date=expiration_date,
        notification_days_before=[1],
    )

    assert notifications[0].scheduled_for.tzinfo is not None
    assert notifications[0].scheduled_for.utcoffset() == timedelta(0)


def test_build_scheduled_notifications_is_sent_defaults_false() -> None:
    expiration_date = _today() + timedelta(days=5)

    notifications = build_scheduled_notifications(
        expiration_date=expiration_date,
        notification_days_before=[1],
    )

    assert notifications[0].is_sent is False
    assert notifications[0].sent_at is None


def test_build_scheduled_notifications_boundary_day_exactly_on_expiration_kept() -> None:
    expiration_date = _today() + timedelta(days=3)

    notifications = build_scheduled_notifications(
        expiration_date=expiration_date,
        notification_days_before=[3],
    )

    assert [n.days_before for n in notifications] == [3]
