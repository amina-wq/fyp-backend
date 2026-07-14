import uuid
from datetime import UTC, datetime, timedelta

import pytest
from beanie import PydanticObjectId
from src.core.firebase import FirebaseService
from src.modules.inventory.models import InventoryItem, InventoryStatus, ScheduledNotification
from src.modules.notifications.service import NotificationService


def _patch_firebase(monkeypatch: pytest.MonkeyPatch, outcomes: dict[str, bool]):
    calls: list[str] = []

    async def _fake_send(token: str, title: str, body: str, data=None) -> bool:
        calls.append(token)
        return outcomes.get(token, False)

    monkeypatch.setattr(FirebaseService, 'send_push_notification', _fake_send)

    return calls


async def _get_user_id(register_user, email: str) -> PydanticObjectId:
    from src.modules.auth.models import User  # noqa: PLC0415

    await register_user(email=email)

    user = await User.find_one(User.email == email)
    assert user is not None

    return user.id


async def _insert_item(
    user_id: PydanticObjectId,
    category_id: str,
    scheduled_for: datetime,
    *,
    status: InventoryStatus = InventoryStatus.ACTIVE,
) -> InventoryItem:
    item = InventoryItem(
        user_id=user_id,
        custom_name='Notification Test Item',
        category_id=PydanticObjectId(category_id),
        expiration_date=(datetime.now(UTC) + timedelta(days=5)).date(),
        status=status,
        scheduled_notifications=[
            ScheduledNotification(days_before=1, scheduled_for=scheduled_for),
        ],
    )
    await item.insert()

    return item


async def test_processes_due_notification_and_marks_sent_on_firebase_success(
    register_user,
    first_category_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = f'token-{uuid.uuid4().hex}'
    calls = _patch_firebase(monkeypatch, {token: True})

    user_id = await _get_user_id(register_user, f'worker.success.{uuid.uuid4().hex}@example.com')

    from src.modules.auth.models import User  # noqa: PLC0415

    user = await User.get(user_id)
    user.fcm_token = token
    await user.save()

    past = datetime.now(UTC) - timedelta(minutes=5)
    item = await _insert_item(user_id, first_category_id, past)

    await NotificationService().process_due_notifications()

    updated_item = await InventoryItem.get(item.id)
    notification = updated_item.scheduled_notifications[0]

    assert notification.is_sent is True
    assert notification.sent_at is not None
    assert calls.count(token) == 1


async def test_does_not_process_notification_not_yet_due(
    register_user,
    first_category_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = f'token-{uuid.uuid4().hex}'
    _patch_firebase(monkeypatch, {token: True})

    user_id = await _get_user_id(register_user, f'worker.not-due.{uuid.uuid4().hex}@example.com')

    from src.modules.auth.models import User  # noqa: PLC0415

    user = await User.get(user_id)
    user.fcm_token = token
    await user.save()

    future = datetime.now(UTC) + timedelta(days=5)
    item = await _insert_item(user_id, first_category_id, future)

    await NotificationService().process_due_notifications()

    updated_item = await InventoryItem.get(item.id)
    notification = updated_item.scheduled_notifications[0]

    assert notification.is_sent is False
    assert notification.sent_at is None


async def test_marks_sent_without_firebase_call_when_user_does_not_exist(
    first_category_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = f'token-{uuid.uuid4().hex}'
    calls = _patch_firebase(monkeypatch, {token: True})

    nonexistent_user_id = PydanticObjectId()
    past = datetime.now(UTC) - timedelta(minutes=5)

    item = await _insert_item(nonexistent_user_id, first_category_id, past)

    await NotificationService().process_due_notifications()

    updated_item = await InventoryItem.get(item.id)
    notification = updated_item.scheduled_notifications[0]

    assert notification.is_sent is True
    assert token not in calls


async def test_marks_sent_without_firebase_call_when_notifications_disabled(
    register_user,
    first_category_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = f'token-{uuid.uuid4().hex}'
    calls = _patch_firebase(monkeypatch, {token: True})

    user_id = await _get_user_id(register_user, f'worker.disabled.{uuid.uuid4().hex}@example.com')

    from src.modules.auth.models import User  # noqa: PLC0415

    user = await User.get(user_id)
    user.fcm_token = token
    user.expiry_notifications_enabled = False
    await user.save()

    past = datetime.now(UTC) - timedelta(minutes=5)
    item = await _insert_item(user_id, first_category_id, past)

    await NotificationService().process_due_notifications()

    updated_item = await InventoryItem.get(item.id)
    notification = updated_item.scheduled_notifications[0]

    assert notification.is_sent is True
    assert token not in calls


async def test_marks_sent_without_firebase_call_when_fcm_token_missing(
    register_user,
    first_category_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _patch_firebase(monkeypatch, {})

    user_id = await _get_user_id(register_user, f'worker.no-token.{uuid.uuid4().hex}@example.com')

    past = datetime.now(UTC) - timedelta(minutes=5)
    item = await _insert_item(user_id, first_category_id, past)

    await NotificationService().process_due_notifications()

    updated_item = await InventoryItem.get(item.id)
    notification = updated_item.scheduled_notifications[0]

    assert notification.is_sent is True
    assert calls == []


async def test_leaves_notification_unsent_when_firebase_fails(
    register_user,
    first_category_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = f'token-{uuid.uuid4().hex}'
    calls = _patch_firebase(monkeypatch, {token: False})

    user_id = await _get_user_id(register_user, f'worker.firebase-fails.{uuid.uuid4().hex}@example.com')

    from src.modules.auth.models import User  # noqa: PLC0415

    user = await User.get(user_id)
    user.fcm_token = token
    await user.save()

    past = datetime.now(UTC) - timedelta(minutes=5)
    item = await _insert_item(user_id, first_category_id, past)

    await NotificationService().process_due_notifications()

    updated_item = await InventoryItem.get(item.id)
    notification = updated_item.scheduled_notifications[0]

    assert notification.is_sent is False
    assert notification.sent_at is None
    assert calls.count(token) == 1


async def test_ignores_notifications_on_non_active_items(
    register_user,
    first_category_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = f'token-{uuid.uuid4().hex}'
    calls = _patch_firebase(monkeypatch, {token: True})

    user_id = await _get_user_id(register_user, f'worker.non-active.{uuid.uuid4().hex}@example.com')

    from src.modules.auth.models import User  # noqa: PLC0415

    user = await User.get(user_id)
    user.fcm_token = token
    await user.save()

    past = datetime.now(UTC) - timedelta(minutes=5)
    item = await _insert_item(user_id, first_category_id, past, status=InventoryStatus.WASTED)

    await NotificationService().process_due_notifications()

    updated_item = await InventoryItem.get(item.id)
    notification = updated_item.scheduled_notifications[0]

    assert notification.is_sent is False
    assert token not in calls
