from datetime import date, timedelta
from http import HTTPStatus

from httpx import AsyncClient


async def _register_user(
    app_client: AsyncClient,
    email: str,
    password: str = 'Settings123!',
) -> dict[str, str]:
    response = await app_client.post(
        '/api/v1/auth/register',
        json={
            'name': 'Settings User',
            'email': email,
            'password': password,
        },
    )

    assert response.status_code == HTTPStatus.CREATED

    return response.json()


async def _auth_headers(access_token: str) -> dict[str, str]:
    return {
        'Authorization': f'Bearer {access_token}',
    }


async def _get_first_category_id(
    app_client: AsyncClient,
    access_token: str,
) -> str:
    response = await app_client.get(
        '/api/v1/categories',
        headers=await _auth_headers(access_token),
    )

    assert response.status_code == HTTPStatus.OK

    categories = response.json()

    assert len(categories) > 0

    return categories[0]['id']


async def test_update_theme_mode(app_client: AsyncClient) -> None:
    tokens = await _register_user(
        app_client=app_client,
        email='settings.theme@example.com',
    )

    response = await app_client.patch(
        '/api/v1/auth/me/settings',
        headers=await _auth_headers(tokens['access_token']),
        json={
            'theme_mode': 'dark',
        },
    )

    assert response.status_code == HTTPStatus.OK

    data = response.json()

    assert data['theme_mode'] == 'dark'


async def test_update_notification_days_before(app_client: AsyncClient) -> None:
    tokens = await _register_user(
        app_client=app_client,
        email='settings.days@example.com',
    )

    response = await app_client.patch(
        '/api/v1/auth/me/settings',
        headers=await _auth_headers(tokens['access_token']),
        json={
            'notification_days_before': [7, 3, 1],
        },
    )

    assert response.status_code == HTTPStatus.OK

    data = response.json()

    assert data['notification_days_before'] == [7, 3, 1]


async def test_update_notification_days_before_rejects_empty_list(
    app_client: AsyncClient,
) -> None:
    tokens = await _register_user(
        app_client=app_client,
        email='settings.empty-days@example.com',
    )

    response = await app_client.patch(
        '/api/v1/auth/me/settings',
        headers=await _auth_headers(tokens['access_token']),
        json={
            'notification_days_before': [],
        },
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


async def test_update_notification_settings_reschedules_existing_inventory_items(
    app_client: AsyncClient,
) -> None:
    tokens = await _register_user(
        app_client=app_client,
        email='settings.reschedule@example.com',
    )

    access_token = tokens['access_token']
    headers = await _auth_headers(access_token)

    category_id = await _get_first_category_id(
        app_client=app_client,
        access_token=access_token,
    )

    expiration_date = date.today() + timedelta(days=10)

    create_response = await app_client.post(
        '/api/v1/inventory',
        headers=headers,
        json={
            'custom_name': 'Milk',
            'category_id': category_id,
            'location': 'fridge',
            'amount': 1,
            'unit': 'pcs',
            'expiration_date': expiration_date.isoformat(),
        },
    )

    assert create_response.status_code == HTTPStatus.CREATED

    created_item = create_response.json()

    assert [item['days_before'] for item in created_item['scheduled_notifications']] == [
        5,
        1,
        0,
    ]

    settings_response = await app_client.patch(
        '/api/v1/auth/me/settings',
        headers=headers,
        json={
            'notification_days_before': [7, 3, 1],
        },
    )

    assert settings_response.status_code == HTTPStatus.OK

    get_item_response = await app_client.get(
        f'/api/v1/inventory/{created_item["id"]}',
        headers=headers,
    )

    assert get_item_response.status_code == HTTPStatus.OK

    updated_item = get_item_response.json()

    assert [item['days_before'] for item in updated_item['scheduled_notifications']] == [
        7,
        3,
        1,
    ]
