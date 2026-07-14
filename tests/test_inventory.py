from datetime import datetime, timedelta
from http import HTTPStatus

import pytest
from httpx import AsyncClient
from src.modules.notifications.scheduling import APP_TIMEZONE


def _today():
    return datetime.now(APP_TIMEZONE).date()


async def test_create_item_with_custom_name_success(
    app_client: AsyncClient,
    register_user,
    auth_headers,
    first_category_id: str,
) -> None:
    tokens = await register_user(email='inventory.create-custom@example.com')

    response = await app_client.post(
        '/api/v1/inventory',
        headers=auth_headers(tokens['access_token']),
        json={
            'custom_name': 'Homemade Soup',
            'category_id': first_category_id,
            'location': 'fridge',
            'amount': 2,
            'unit': 'l',
            'expiration_date': (_today() + timedelta(days=5)).isoformat(),
        },
    )

    assert response.status_code == HTTPStatus.CREATED

    data = response.json()

    assert data['display_name'] == 'Homemade Soup'
    assert data['status'] == 'active'
    assert data['category']['id'] == first_category_id


async def test_create_item_with_product_id_success(
    app_client: AsyncClient,
    register_user,
    auth_headers,
    first_category_id: str,
) -> None:
    tokens = await register_user(email='inventory.create-product-id@example.com')
    headers = auth_headers(tokens['access_token'])

    product_response = await app_client.post(
        '/api/v1/products/manual',
        headers=headers,
        json={'barcode': '9000000000001', 'name': 'Linked Product'},
    )
    product_id = product_response.json()['id']

    response = await app_client.post(
        '/api/v1/inventory',
        headers=headers,
        json={
            'product_id': product_id,
            'category_id': first_category_id,
            'expiration_date': (_today() + timedelta(days=5)).isoformat(),
        },
    )

    assert response.status_code == HTTPStatus.CREATED

    data = response.json()

    assert data['product_id'] == product_id
    assert data['display_name'] == 'Linked Product'
    assert data['barcode'] == '9000000000001'


async def test_create_item_with_barcode_fetches_product(
    app_client: AsyncClient,
    register_user,
    auth_headers,
    first_category_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tokens = await register_user(email='inventory.create-barcode@example.com')
    barcode = '9000000000002'

    async def _fetch(_barcode: str) -> dict | None:
        return {
            'barcode': barcode,
            'name': 'Barcode Fetched Product',
            'brand': None,
            'tags': [],
            'image_url': None,
            'quantity': None,
            'source': 'off',
        }

    monkeypatch.setattr('src.modules.products.services.fetch_product_by_barcode', _fetch)

    response = await app_client.post(
        '/api/v1/inventory',
        headers=auth_headers(tokens['access_token']),
        json={
            'barcode': barcode,
            'category_id': first_category_id,
            'expiration_date': (_today() + timedelta(days=5)).isoformat(),
        },
    )

    assert response.status_code == HTTPStatus.CREATED
    assert response.json()['display_name'] == 'Barcode Fetched Product'


async def test_create_item_rejects_without_any_identifier(
    app_client: AsyncClient,
    register_user,
    auth_headers,
    first_category_id: str,
) -> None:
    tokens = await register_user(email='inventory.create-no-identifier@example.com')

    response = await app_client.post(
        '/api/v1/inventory',
        headers=auth_headers(tokens['access_token']),
        json={
            'category_id': first_category_id,
            'expiration_date': (_today() + timedelta(days=5)).isoformat(),
        },
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


async def test_create_item_rejects_missing_token(app_client: AsyncClient, first_category_id: str) -> None:
    response = await app_client.post(
        '/api/v1/inventory',
        json={
            'custom_name': 'No Auth Item',
            'category_id': first_category_id,
            'expiration_date': (_today() + timedelta(days=5)).isoformat(),
        },
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED


async def test_create_item_rejects_invalid_category_id(
    app_client: AsyncClient,
    register_user,
    auth_headers,
) -> None:
    tokens = await register_user(email='inventory.create-invalid-category@example.com')

    response = await app_client.post(
        '/api/v1/inventory',
        headers=auth_headers(tokens['access_token']),
        json={
            'custom_name': 'Bad Category Item',
            'category_id': 'not-an-object-id',
            'expiration_date': (_today() + timedelta(days=5)).isoformat(),
        },
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST


async def test_create_item_returns_404_for_nonexistent_category(
    app_client: AsyncClient,
    register_user,
    auth_headers,
) -> None:
    tokens = await register_user(email='inventory.create-404-category@example.com')

    response = await app_client.post(
        '/api/v1/inventory',
        headers=auth_headers(tokens['access_token']),
        json={
            'custom_name': 'No Category Item',
            'category_id': '507f1f77bcf86cd799439011',
            'expiration_date': (_today() + timedelta(days=5)).isoformat(),
        },
    )

    assert response.status_code == HTTPStatus.NOT_FOUND


async def test_create_item_returns_404_for_nonexistent_product_id(
    app_client: AsyncClient,
    register_user,
    auth_headers,
    first_category_id: str,
) -> None:
    tokens = await register_user(email='inventory.create-404-product@example.com')

    response = await app_client.post(
        '/api/v1/inventory',
        headers=auth_headers(tokens['access_token']),
        json={
            'product_id': '507f1f77bcf86cd799439011',
            'category_id': first_category_id,
            'expiration_date': (_today() + timedelta(days=5)).isoformat(),
        },
    )

    assert response.status_code == HTTPStatus.NOT_FOUND


async def test_create_item_rejects_mismatched_product_and_barcode(
    app_client: AsyncClient,
    register_user,
    auth_headers,
    first_category_id: str,
) -> None:
    tokens = await register_user(email='inventory.create-mismatch@example.com')
    headers = auth_headers(tokens['access_token'])

    product_response = await app_client.post(
        '/api/v1/products/manual',
        headers=headers,
        json={'barcode': '9000000000003', 'name': 'Mismatch Product'},
    )
    product_id = product_response.json()['id']

    response = await app_client.post(
        '/api/v1/inventory',
        headers=headers,
        json={
            'product_id': product_id,
            'barcode': '9999999999999',
            'category_id': first_category_id,
            'expiration_date': (_today() + timedelta(days=5)).isoformat(),
        },
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json()['detail'] == 'Product id and barcode do not match'


async def test_create_item_schedules_notifications_skipping_past_days(
    app_client: AsyncClient,
    register_user,
    auth_headers,
    first_category_id: str,
) -> None:
    tokens = await register_user(email='inventory.create-schedule@example.com')

    response = await app_client.post(
        '/api/v1/inventory',
        headers=auth_headers(tokens['access_token']),
        json={
            'custom_name': 'Soon Expiring',
            'category_id': first_category_id,
            'expiration_date': (_today() + timedelta(days=1)).isoformat(),
        },
    )

    assert response.status_code == HTTPStatus.CREATED

    scheduled = response.json()['scheduled_notifications']
    days_before_values = [item['days_before'] for item in scheduled]

    assert days_before_values == [1, 0]


async def test_get_items_returns_only_active_sorted_newest_first(
    app_client: AsyncClient,
    register_user,
    auth_headers,
    first_category_id: str,
    create_inventory_item,
) -> None:
    tokens = await register_user(email='inventory.list-sorted@example.com')
    access_token = tokens['access_token']
    headers = auth_headers(access_token)

    first_item = await create_inventory_item(access_token, first_category_id, custom_name='First Item')
    second_item = await create_inventory_item(access_token, first_category_id, custom_name='Second Item')

    await app_client.patch(
        f'/api/v1/inventory/{first_item["id"]}/consume',
        headers=headers,
    )

    response = await app_client.get('/api/v1/inventory', headers=headers)

    assert response.status_code == HTTPStatus.OK

    items = response.json()
    item_ids = [item['id'] for item in items]

    assert first_item['id'] not in item_ids
    assert item_ids[0] == second_item['id']


async def test_get_items_filters_by_category_id(
    app_client: AsyncClient,
    register_user,
    auth_headers,
    first_category_id: str,
    get_category_id_by_key,
    create_inventory_item,
) -> None:
    tokens = await register_user(email='inventory.filter-category@example.com')
    access_token = tokens['access_token']
    headers = auth_headers(access_token)

    meat_category_id = await get_category_id_by_key('meat', access_token)

    dairy_item = await create_inventory_item(access_token, first_category_id, custom_name='Dairy Filter Item')
    await create_inventory_item(access_token, meat_category_id, custom_name='Meat Filter Item')

    response = await app_client.get(
        '/api/v1/inventory',
        headers=headers,
        params={'category_id': first_category_id},
    )

    assert response.status_code == HTTPStatus.OK

    items = response.json()

    assert all(item['category']['id'] == first_category_id for item in items)
    assert any(item['id'] == dairy_item['id'] for item in items)


async def test_get_items_filters_by_expiry_state(
    app_client: AsyncClient,
    register_user,
    auth_headers,
    first_category_id: str,
) -> None:
    tokens = await register_user(email='inventory.filter-expiry@example.com')
    access_token = tokens['access_token']
    headers = auth_headers(access_token)

    fresh_response = await app_client.post(
        '/api/v1/inventory',
        headers=headers,
        json={
            'custom_name': 'Fresh Filter Item',
            'category_id': first_category_id,
            'expiration_date': (_today() + timedelta(days=30)).isoformat(),
        },
    )
    expiring_response = await app_client.post(
        '/api/v1/inventory',
        headers=headers,
        json={
            'custom_name': 'Expiring Filter Item',
            'category_id': first_category_id,
            'expiration_date': _today().isoformat(),
        },
    )

    fresh_id = fresh_response.json()['id']
    expiring_id = expiring_response.json()['id']

    response = await app_client.get(
        '/api/v1/inventory',
        headers=headers,
        params={'expiry_state': 'expiring'},
    )

    assert response.status_code == HTTPStatus.OK

    items = response.json()
    item_ids = {item['id'] for item in items}

    assert expiring_id in item_ids
    assert fresh_id not in item_ids


async def test_get_item_by_id_success(
    app_client: AsyncClient,
    register_user,
    auth_headers,
    first_category_id: str,
    create_inventory_item,
) -> None:
    tokens = await register_user(email='inventory.get-by-id@example.com')
    access_token = tokens['access_token']

    item = await create_inventory_item(access_token, first_category_id)

    response = await app_client.get(
        f'/api/v1/inventory/{item["id"]}',
        headers=auth_headers(access_token),
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json()['id'] == item['id']


async def test_get_item_by_id_rejects_invalid_id(
    app_client: AsyncClient,
    register_user,
    auth_headers,
) -> None:
    tokens = await register_user(email='inventory.get-invalid-id@example.com')

    response = await app_client.get(
        '/api/v1/inventory/not-an-object-id',
        headers=auth_headers(tokens['access_token']),
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST


async def test_get_item_by_id_returns_404_for_other_users_item(
    app_client: AsyncClient,
    register_user,
    auth_headers,
    first_category_id: str,
    create_inventory_item,
) -> None:
    owner_tokens = await register_user(email='inventory.owner@example.com')
    other_tokens = await register_user(email='inventory.other-user@example.com')

    item = await create_inventory_item(owner_tokens['access_token'], first_category_id)

    response = await app_client.get(
        f'/api/v1/inventory/{item["id"]}',
        headers=auth_headers(other_tokens['access_token']),
    )

    assert response.status_code == HTTPStatus.NOT_FOUND


async def test_update_item_success(
    app_client: AsyncClient,
    register_user,
    auth_headers,
    first_category_id: str,
    create_inventory_item,
) -> None:
    tokens = await register_user(email='inventory.update@example.com')
    access_token = tokens['access_token']
    headers = auth_headers(access_token)

    item = await create_inventory_item(access_token, first_category_id, custom_name='Before Update')

    response = await app_client.patch(
        f'/api/v1/inventory/{item["id"]}',
        headers=headers,
        json={'custom_name': 'After Update', 'amount': 3},
    )

    assert response.status_code == HTTPStatus.OK

    data = response.json()

    assert data['custom_name'] == 'After Update'
    assert data['amount'] == 3


async def test_update_item_rejects_empty_body(
    app_client: AsyncClient,
    register_user,
    auth_headers,
    first_category_id: str,
    create_inventory_item,
) -> None:
    tokens = await register_user(email='inventory.update-empty@example.com')
    access_token = tokens['access_token']

    item = await create_inventory_item(access_token, first_category_id)

    response = await app_client.patch(
        f'/api/v1/inventory/{item["id"]}',
        headers=auth_headers(access_token),
        json={},
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json()['detail'] == 'Nothing to update'


async def test_update_item_reschedules_on_expiration_date_change(
    app_client: AsyncClient,
    register_user,
    auth_headers,
    first_category_id: str,
    create_inventory_item,
) -> None:
    tokens = await register_user(email='inventory.update-reschedule@example.com')
    access_token = tokens['access_token']

    item = await create_inventory_item(access_token, first_category_id)

    new_expiration = _today() + timedelta(days=1)

    response = await app_client.patch(
        f'/api/v1/inventory/{item["id"]}',
        headers=auth_headers(access_token),
        json={'expiration_date': new_expiration.isoformat()},
    )

    assert response.status_code == HTTPStatus.OK

    days_before_values = [n['days_before'] for n in response.json()['scheduled_notifications']]

    assert days_before_values == [1, 0]


async def test_update_item_returns_404_for_other_users_item(
    app_client: AsyncClient,
    register_user,
    auth_headers,
    first_category_id: str,
    create_inventory_item,
) -> None:
    owner_tokens = await register_user(email='inventory.update-owner@example.com')
    other_tokens = await register_user(email='inventory.update-other@example.com')

    item = await create_inventory_item(owner_tokens['access_token'], first_category_id)

    response = await app_client.patch(
        f'/api/v1/inventory/{item["id"]}',
        headers=auth_headers(other_tokens['access_token']),
        json={'custom_name': 'Hijacked'},
    )

    assert response.status_code == HTTPStatus.NOT_FOUND


async def test_consume_item_marks_status_and_notifications_sent(
    app_client: AsyncClient,
    register_user,
    auth_headers,
    first_category_id: str,
    create_inventory_item,
) -> None:
    tokens = await register_user(email='inventory.consume@example.com')
    access_token = tokens['access_token']

    item = await create_inventory_item(access_token, first_category_id)

    response = await app_client.patch(
        f'/api/v1/inventory/{item["id"]}/consume',
        headers=auth_headers(access_token),
    )

    assert response.status_code == HTTPStatus.OK

    data = response.json()

    assert data['status'] == 'consumed'
    assert all(n['is_sent'] for n in data['scheduled_notifications'])


async def test_waste_item_marks_status_wasted(
    app_client: AsyncClient,
    register_user,
    auth_headers,
    first_category_id: str,
    create_inventory_item,
) -> None:
    tokens = await register_user(email='inventory.waste@example.com')
    access_token = tokens['access_token']

    item = await create_inventory_item(access_token, first_category_id)

    response = await app_client.patch(
        f'/api/v1/inventory/{item["id"]}/waste',
        headers=auth_headers(access_token),
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json()['status'] == 'wasted'


async def test_delete_item_soft_deletes_and_hides_item(
    app_client: AsyncClient,
    register_user,
    auth_headers,
    first_category_id: str,
    create_inventory_item,
) -> None:
    tokens = await register_user(email='inventory.delete@example.com')
    access_token = tokens['access_token']
    headers = auth_headers(access_token)

    item = await create_inventory_item(access_token, first_category_id)

    delete_response = await app_client.delete(f'/api/v1/inventory/{item["id"]}', headers=headers)

    assert delete_response.status_code == HTTPStatus.OK
    assert delete_response.json()['detail'] == 'Inventory item deleted'

    get_response = await app_client.get(f'/api/v1/inventory/{item["id"]}', headers=headers)

    assert get_response.status_code == HTTPStatus.NOT_FOUND


async def test_get_stats_buckets_are_correct(
    app_client: AsyncClient,
    register_user,
    auth_headers,
    first_category_id: str,
) -> None:
    tokens = await register_user(email='inventory.stats@example.com')
    access_token = tokens['access_token']
    headers = auth_headers(access_token)

    today = _today()

    dates = {
        'expired': today - timedelta(days=1),
        'tomorrow': today + timedelta(days=1),
        'in_5_days': today + timedelta(days=5),
        'in_6_days': today + timedelta(days=6),
    }

    for label, expiration_date in dates.items():
        response = await app_client.post(
            '/api/v1/inventory',
            headers=headers,
            json={
                'custom_name': f'Stats Item {label}',
                'category_id': first_category_id,
                'expiration_date': expiration_date.isoformat(),
            },
        )
        assert response.status_code == HTTPStatus.CREATED

    response = await app_client.get('/api/v1/inventory/stats', headers=headers)

    assert response.status_code == HTTPStatus.OK

    data = response.json()

    assert data['expired_count'] == 1
    assert data['expiring_tomorrow_count'] == 1
    assert data['expiring_in_5_days_count'] == 1
    assert data['fresh_count'] == 1


async def test_upload_item_image_success(
    app_client: AsyncClient,
    register_user,
    auth_headers,
    first_category_id: str,
    create_inventory_item,
) -> None:
    tokens = await register_user(email='inventory.image-upload@example.com')
    access_token = tokens['access_token']
    headers = auth_headers(access_token)

    item = await create_inventory_item(access_token, first_category_id)

    response = await app_client.post(
        f'/api/v1/inventory/{item["id"]}/image',
        headers=headers,
        files={'image': ('photo.jpg', b'fake-jpeg-bytes', 'image/jpeg')},
    )

    assert response.status_code == HTTPStatus.OK

    data = response.json()

    assert data['item_image_url'] is not None
    assert 'test-bucket' in data['item_image_url']


async def test_upload_item_image_rejects_bad_content_type(
    app_client: AsyncClient,
    register_user,
    auth_headers,
    first_category_id: str,
    create_inventory_item,
) -> None:
    tokens = await register_user(email='inventory.image-bad-type@example.com')
    access_token = tokens['access_token']

    item = await create_inventory_item(access_token, first_category_id)

    response = await app_client.post(
        f'/api/v1/inventory/{item["id"]}/image',
        headers=auth_headers(access_token),
        files={'image': ('photo.gif', b'fake-gif-bytes', 'image/gif')},
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST


async def test_upload_item_image_rejects_oversized(
    app_client: AsyncClient,
    register_user,
    auth_headers,
    first_category_id: str,
    create_inventory_item,
) -> None:
    tokens = await register_user(email='inventory.image-too-large@example.com')
    access_token = tokens['access_token']

    item = await create_inventory_item(access_token, first_category_id)

    oversized_content = b'0' * (5 * 1024 * 1024 + 1)

    response = await app_client.post(
        f'/api/v1/inventory/{item["id"]}/image',
        headers=auth_headers(access_token),
        files={'image': ('photo.jpg', oversized_content, 'image/jpeg')},
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json()['detail'] == 'Image size must be less than 5MB'


async def test_delete_item_image_clears_image(
    app_client: AsyncClient,
    register_user,
    auth_headers,
    first_category_id: str,
    create_inventory_item,
) -> None:
    tokens = await register_user(email='inventory.image-delete@example.com')
    access_token = tokens['access_token']
    headers = auth_headers(access_token)

    item = await create_inventory_item(access_token, first_category_id)

    await app_client.post(
        f'/api/v1/inventory/{item["id"]}/image',
        headers=headers,
        files={'image': ('photo.jpg', b'fake-jpeg-bytes', 'image/jpeg')},
    )

    response = await app_client.delete(f'/api/v1/inventory/{item["id"]}/image', headers=headers)

    assert response.status_code == HTTPStatus.OK
    assert response.json()['item_image_url'] is None
