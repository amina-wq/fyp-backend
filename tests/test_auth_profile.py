from http import HTTPStatus

from httpx import AsyncClient


async def test_update_name_success(app_client: AsyncClient, register_user, auth_headers) -> None:
    tokens = await register_user(email='profile.name@example.com')

    response = await app_client.patch(
        '/api/v1/auth/me/name',
        headers=auth_headers(tokens['access_token']),
        json={'name': 'New Name'},
    )

    assert response.status_code == HTTPStatus.OK

    data = response.json()

    assert data['name'] == 'New Name'


async def test_update_name_rejects_too_short(app_client: AsyncClient, register_user, auth_headers) -> None:
    tokens = await register_user(email='profile.short-name@example.com')

    response = await app_client.patch(
        '/api/v1/auth/me/name',
        headers=auth_headers(tokens['access_token']),
        json={'name': 'A'},
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


async def test_update_name_rejects_too_long(app_client: AsyncClient, register_user, auth_headers) -> None:
    tokens = await register_user(email='profile.long-name@example.com')

    response = await app_client.patch(
        '/api/v1/auth/me/name',
        headers=auth_headers(tokens['access_token']),
        json={'name': 'A' * 101},
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


async def test_update_name_rejects_missing_token(app_client: AsyncClient) -> None:
    response = await app_client.patch(
        '/api/v1/auth/me/name',
        json={'name': 'New Name'},
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED


async def test_update_fcm_token_success(app_client: AsyncClient, register_user, auth_headers) -> None:
    tokens = await register_user(email='profile.fcm@example.com')

    response = await app_client.patch(
        '/api/v1/auth/fcm-token',
        headers=auth_headers(tokens['access_token']),
        json={'fcm_token': 'some-fcm-token-value'},
    )

    assert response.status_code == HTTPStatus.OK

    data = response.json()

    assert data['fcm_token'] == 'some-fcm-token-value'


async def test_update_fcm_token_can_clear_token(app_client: AsyncClient, register_user, auth_headers) -> None:
    tokens = await register_user(email='profile.fcm-clear@example.com')

    headers = auth_headers(tokens['access_token'])

    await app_client.patch(
        '/api/v1/auth/fcm-token',
        headers=headers,
        json={'fcm_token': 'token-to-clear'},
    )

    response = await app_client.patch(
        '/api/v1/auth/fcm-token',
        headers=headers,
        json={'fcm_token': None},
    )

    assert response.status_code == HTTPStatus.OK

    data = response.json()

    assert data['fcm_token'] is None


async def test_update_fcm_token_rejects_too_long(app_client: AsyncClient, register_user, auth_headers) -> None:
    tokens = await register_user(email='profile.fcm-long@example.com')

    response = await app_client.patch(
        '/api/v1/auth/fcm-token',
        headers=auth_headers(tokens['access_token']),
        json={'fcm_token': 'a' * 501},
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


async def test_get_me_returns_full_profile_shape(app_client: AsyncClient, register_user, auth_headers) -> None:
    tokens = await register_user(email='profile.shape@example.com', name='Shape User')

    response = await app_client.get(
        '/api/v1/auth/me',
        headers=auth_headers(tokens['access_token']),
    )

    assert response.status_code == HTTPStatus.OK

    data = response.json()

    assert data['name'] == 'Shape User'
    assert data['role'] == 'user'
    assert data['is_active'] is True
    assert data['theme_mode'] == 'system'
    assert data['account_type'] == 'personal'
    assert data['notification_days_before'] == [5, 1, 0]
    assert data['expiry_notifications_enabled'] is True
