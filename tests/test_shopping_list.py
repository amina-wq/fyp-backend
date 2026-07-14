from http import HTTPStatus

from httpx import AsyncClient


async def test_create_shopping_list_item_success(
    app_client: AsyncClient,
    register_user,
    auth_headers,
    first_category_id: str,
) -> None:
    tokens = await register_user(email='shopping.create@example.com')

    response = await app_client.post(
        '/api/v1/shopping-list',
        headers=auth_headers(tokens['access_token']),
        json={
            'name': 'Eggs',
            'category_id': first_category_id,
            'amount': 12,
            'unit': 'pcs',
        },
    )

    assert response.status_code == HTTPStatus.CREATED

    data = response.json()

    assert data['name'] == 'Eggs'
    assert data['is_checked'] is False
    assert data['source'] == 'manual'
    assert data['category']['id'] == first_category_id


async def test_create_shopping_list_item_rejects_missing_token(
    app_client: AsyncClient,
    first_category_id: str,
) -> None:
    response = await app_client.post(
        '/api/v1/shopping-list',
        json={'name': 'No Auth Item', 'category_id': first_category_id},
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED


async def test_create_shopping_list_item_rejects_missing_name(
    app_client: AsyncClient,
    register_user,
    auth_headers,
    first_category_id: str,
) -> None:
    tokens = await register_user(email='shopping.create-no-name@example.com')

    response = await app_client.post(
        '/api/v1/shopping-list',
        headers=auth_headers(tokens['access_token']),
        json={'category_id': first_category_id},
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


async def test_create_shopping_list_item_returns_404_for_nonexistent_category(
    app_client: AsyncClient,
    register_user,
    auth_headers,
) -> None:
    tokens = await register_user(email='shopping.create-404-category@example.com')

    response = await app_client.post(
        '/api/v1/shopping-list',
        headers=auth_headers(tokens['access_token']),
        json={'name': 'Ghost Category Item', 'category_id': '507f1f77bcf86cd799439011'},
    )

    assert response.status_code == HTTPStatus.NOT_FOUND


async def test_get_shopping_list_items_sorted_oldest_first(
    app_client: AsyncClient,
    register_user,
    auth_headers,
    first_category_id: str,
) -> None:
    tokens = await register_user(email='shopping.list-sorted@example.com')
    headers = auth_headers(tokens['access_token'])

    first_response = await app_client.post(
        '/api/v1/shopping-list',
        headers=headers,
        json={'name': 'First Added', 'category_id': first_category_id},
    )
    second_response = await app_client.post(
        '/api/v1/shopping-list',
        headers=headers,
        json={'name': 'Second Added', 'category_id': first_category_id},
    )

    response = await app_client.get('/api/v1/shopping-list', headers=headers)

    assert response.status_code == HTTPStatus.OK

    items = response.json()
    item_ids = [item['id'] for item in items]

    assert item_ids.index(first_response.json()['id']) < item_ids.index(second_response.json()['id'])


async def test_get_shopping_list_items_excludes_checked_when_requested(
    app_client: AsyncClient,
    register_user,
    auth_headers,
    first_category_id: str,
) -> None:
    tokens = await register_user(email='shopping.exclude-checked@example.com')
    headers = auth_headers(tokens['access_token'])

    unchecked_response = await app_client.post(
        '/api/v1/shopping-list',
        headers=headers,
        json={'name': 'Stays Unchecked', 'category_id': first_category_id},
    )
    checked_response = await app_client.post(
        '/api/v1/shopping-list',
        headers=headers,
        json={'name': 'Gets Checked', 'category_id': first_category_id},
    )

    await app_client.patch(
        f'/api/v1/shopping-list/{checked_response.json()["id"]}/check',
        headers=headers,
    )

    response = await app_client.get(
        '/api/v1/shopping-list',
        headers=headers,
        params={'include_checked': False},
    )

    assert response.status_code == HTTPStatus.OK

    item_ids = {item['id'] for item in response.json()}

    assert unchecked_response.json()['id'] in item_ids
    assert checked_response.json()['id'] not in item_ids


async def test_update_shopping_list_item_success(
    app_client: AsyncClient,
    register_user,
    auth_headers,
    first_category_id: str,
) -> None:
    tokens = await register_user(email='shopping.update@example.com')
    headers = auth_headers(tokens['access_token'])

    create_response = await app_client.post(
        '/api/v1/shopping-list',
        headers=headers,
        json={'name': 'Before Update', 'category_id': first_category_id},
    )
    item_id = create_response.json()['id']

    response = await app_client.patch(
        f'/api/v1/shopping-list/{item_id}',
        headers=headers,
        json={'name': 'After Update', 'amount': 5},
    )

    assert response.status_code == HTTPStatus.OK

    data = response.json()

    assert data['name'] == 'After Update'
    assert data['amount'] == 5


async def test_update_shopping_list_item_rejects_invalid_id(
    app_client: AsyncClient,
    register_user,
    auth_headers,
) -> None:
    tokens = await register_user(email='shopping.update-invalid-id@example.com')

    response = await app_client.patch(
        '/api/v1/shopping-list/not-an-object-id',
        headers=auth_headers(tokens['access_token']),
        json={'name': 'Whatever'},
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST


async def test_update_shopping_list_item_returns_404_for_other_users_item(
    app_client: AsyncClient,
    register_user,
    auth_headers,
    first_category_id: str,
) -> None:
    owner_tokens = await register_user(email='shopping.update-owner@example.com')
    other_tokens = await register_user(email='shopping.update-other@example.com')

    create_response = await app_client.post(
        '/api/v1/shopping-list',
        headers=auth_headers(owner_tokens['access_token']),
        json={'name': 'Owned Item', 'category_id': first_category_id},
    )
    item_id = create_response.json()['id']

    response = await app_client.patch(
        f'/api/v1/shopping-list/{item_id}',
        headers=auth_headers(other_tokens['access_token']),
        json={'name': 'Hijacked'},
    )

    assert response.status_code == HTTPStatus.NOT_FOUND


async def test_toggle_checked_flips_state_and_back(
    app_client: AsyncClient,
    register_user,
    auth_headers,
    first_category_id: str,
) -> None:
    tokens = await register_user(email='shopping.toggle@example.com')
    headers = auth_headers(tokens['access_token'])

    create_response = await app_client.post(
        '/api/v1/shopping-list',
        headers=headers,
        json={'name': 'Toggle Item', 'category_id': first_category_id},
    )
    item_id = create_response.json()['id']

    first_toggle = await app_client.patch(f'/api/v1/shopping-list/{item_id}/check', headers=headers)
    assert first_toggle.status_code == HTTPStatus.OK
    assert first_toggle.json()['is_checked'] is True

    second_toggle = await app_client.patch(f'/api/v1/shopping-list/{item_id}/check', headers=headers)
    assert second_toggle.status_code == HTTPStatus.OK
    assert second_toggle.json()['is_checked'] is False


async def test_delete_shopping_list_item_success(
    app_client: AsyncClient,
    register_user,
    auth_headers,
    first_category_id: str,
) -> None:
    tokens = await register_user(email='shopping.delete@example.com')
    headers = auth_headers(tokens['access_token'])

    create_response = await app_client.post(
        '/api/v1/shopping-list',
        headers=headers,
        json={'name': 'To Delete', 'category_id': first_category_id},
    )
    item_id = create_response.json()['id']

    delete_response = await app_client.delete(f'/api/v1/shopping-list/{item_id}', headers=headers)

    assert delete_response.status_code == HTTPStatus.OK
    assert delete_response.json()['detail'] == 'Shopping list item deleted'

    update_response = await app_client.patch(
        f'/api/v1/shopping-list/{item_id}',
        headers=headers,
        json={'name': 'Should not work'},
    )

    assert update_response.status_code == HTTPStatus.NOT_FOUND


async def test_delete_shopping_list_item_returns_404_for_other_users_item(
    app_client: AsyncClient,
    register_user,
    auth_headers,
    first_category_id: str,
) -> None:
    owner_tokens = await register_user(email='shopping.delete-owner@example.com')
    other_tokens = await register_user(email='shopping.delete-other@example.com')

    create_response = await app_client.post(
        '/api/v1/shopping-list',
        headers=auth_headers(owner_tokens['access_token']),
        json={'name': 'Protected Item', 'category_id': first_category_id},
    )
    item_id = create_response.json()['id']

    response = await app_client.delete(
        f'/api/v1/shopping-list/{item_id}',
        headers=auth_headers(other_tokens['access_token']),
    )

    assert response.status_code == HTTPStatus.NOT_FOUND


async def test_clear_checked_deletes_only_checked_items(
    app_client: AsyncClient,
    register_user,
    auth_headers,
    first_category_id: str,
) -> None:
    tokens = await register_user(email='shopping.clear-checked@example.com')
    headers = auth_headers(tokens['access_token'])

    unchecked_response = await app_client.post(
        '/api/v1/shopping-list',
        headers=headers,
        json={'name': 'Stays', 'category_id': first_category_id},
    )
    checked_one = await app_client.post(
        '/api/v1/shopping-list',
        headers=headers,
        json={'name': 'Checked One', 'category_id': first_category_id},
    )
    checked_two = await app_client.post(
        '/api/v1/shopping-list',
        headers=headers,
        json={'name': 'Checked Two', 'category_id': first_category_id},
    )

    await app_client.patch(f'/api/v1/shopping-list/{checked_one.json()["id"]}/check', headers=headers)
    await app_client.patch(f'/api/v1/shopping-list/{checked_two.json()["id"]}/check', headers=headers)

    response = await app_client.delete('/api/v1/shopping-list/checked', headers=headers)

    assert response.status_code == HTTPStatus.OK
    assert response.json()['detail'] == 'Deleted 2 checked shopping list items'

    remaining_response = await app_client.get('/api/v1/shopping-list', headers=headers)
    remaining_ids = {item['id'] for item in remaining_response.json()}

    assert remaining_ids == {unchecked_response.json()['id']}


async def test_clear_checked_with_no_checked_items_returns_zero(
    app_client: AsyncClient,
    register_user,
    auth_headers,
) -> None:
    tokens = await register_user(email='shopping.clear-none@example.com')

    response = await app_client.delete(
        '/api/v1/shopping-list/checked',
        headers=auth_headers(tokens['access_token']),
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json()['detail'] == 'Deleted 0 checked shopping list items'
