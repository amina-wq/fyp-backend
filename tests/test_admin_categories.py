from http import HTTPStatus

from httpx import AsyncClient


async def test_admin_endpoint_rejects_missing_token(app_client: AsyncClient) -> None:
    response = await app_client.get('/api/v1/admin/categories')

    assert response.status_code == HTTPStatus.UNAUTHORIZED


async def test_admin_endpoint_rejects_regular_user(
    app_client: AsyncClient,
    register_user,
    auth_headers,
) -> None:
    tokens = await register_user(email='admin.regular-user@example.com')

    response = await app_client.get(
        '/api/v1/admin/categories',
        headers=auth_headers(tokens['access_token']),
    )

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert response.json()['detail'] == 'Admin access required'


async def test_admin_can_list_all_categories_including_inactive(
    app_client: AsyncClient,
    make_admin_user,
    auth_headers,
) -> None:
    admin_tokens = await make_admin_user(email='admin.list-all@example.com')
    headers = auth_headers(admin_tokens['access_token'])

    create_response = await app_client.post(
        '/api/v1/admin/categories',
        headers=headers,
        json={'key': 'temp_admin_list', 'name': 'Temp Category', 'sort_order': 1000},
    )
    category_id = create_response.json()['id']

    await app_client.delete(f'/api/v1/admin/categories/{category_id}', headers=headers)

    response = await app_client.get('/api/v1/admin/categories', headers=headers)

    assert response.status_code == HTTPStatus.OK

    categories = response.json()
    matching = [category for category in categories if category['id'] == category_id]

    assert len(matching) == 1
    assert matching[0]['is_active'] is False


async def test_admin_create_category_success(
    app_client: AsyncClient,
    make_admin_user,
    auth_headers,
) -> None:
    admin_tokens = await make_admin_user(email='admin.create@example.com')

    response = await app_client.post(
        '/api/v1/admin/categories',
        headers=auth_headers(admin_tokens['access_token']),
        json={
            'key': 'exotic_fruits',
            'name': 'Exotic Fruits',
            'description': 'Rare fruits',
            'color_hex': '#ABCDEF',
            'sort_order': 50,
        },
    )

    assert response.status_code == HTTPStatus.CREATED

    data = response.json()

    assert data['key'] == 'exotic_fruits'
    assert data['is_active'] is True
    assert data['is_default'] is False


async def test_admin_create_category_normalizes_key(
    app_client: AsyncClient,
    make_admin_user,
    auth_headers,
) -> None:
    admin_tokens = await make_admin_user(email='admin.normalize-key@example.com')
    headers = auth_headers(admin_tokens['access_token'])

    response = await app_client.post(
        '/api/v1/admin/categories',
        headers=headers,
        json={'key': '  Spicy Snacks  ', 'name': 'Spicy Snacks', 'sort_order': 1000},
    )

    assert response.status_code == HTTPStatus.CREATED
    assert response.json()['key'] == 'spicy_snacks'

    duplicate_response = await app_client.post(
        '/api/v1/admin/categories',
        headers=headers,
        json={'key': 'spicy_snacks', 'name': 'Spicy Snacks Again'},
    )

    assert duplicate_response.status_code == HTTPStatus.BAD_REQUEST
    assert duplicate_response.json()['detail'] == 'Category with this key already exists'


async def test_admin_create_category_rejects_missing_name(
    app_client: AsyncClient,
    make_admin_user,
    auth_headers,
) -> None:
    admin_tokens = await make_admin_user(email='admin.create-missing-name@example.com')

    response = await app_client.post(
        '/api/v1/admin/categories',
        headers=auth_headers(admin_tokens['access_token']),
        json={'key': 'missing_name'},
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


async def test_admin_update_category_success(
    app_client: AsyncClient,
    make_admin_user,
    auth_headers,
) -> None:
    admin_tokens = await make_admin_user(email='admin.update@example.com')
    headers = auth_headers(admin_tokens['access_token'])

    create_response = await app_client.post(
        '/api/v1/admin/categories',
        headers=headers,
        json={'key': 'update_target', 'name': 'Update Target', 'sort_order': 1000},
    )
    category_id = create_response.json()['id']

    update_response = await app_client.patch(
        f'/api/v1/admin/categories/{category_id}',
        headers=headers,
        json={'name': '  Updated Name  ', 'sort_order': 42},
    )

    assert update_response.status_code == HTTPStatus.OK

    data = update_response.json()

    assert data['name'] == 'Updated Name'
    assert data['sort_order'] == 42


async def test_admin_update_category_rejects_empty_body(
    app_client: AsyncClient,
    make_admin_user,
    auth_headers,
) -> None:
    admin_tokens = await make_admin_user(email='admin.update-empty@example.com')
    headers = auth_headers(admin_tokens['access_token'])

    create_response = await app_client.post(
        '/api/v1/admin/categories',
        headers=headers,
        json={'key': 'empty_update_target', 'name': 'Empty Update Target', 'sort_order': 1000},
    )
    category_id = create_response.json()['id']

    response = await app_client.patch(
        f'/api/v1/admin/categories/{category_id}',
        headers=headers,
        json={},
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json()['detail'] == 'Nothing to update'


async def test_admin_update_category_returns_404_for_nonexistent(
    app_client: AsyncClient,
    make_admin_user,
    auth_headers,
) -> None:
    admin_tokens = await make_admin_user(email='admin.update-404@example.com')

    response = await app_client.patch(
        '/api/v1/admin/categories/507f1f77bcf86cd799439011',
        headers=auth_headers(admin_tokens['access_token']),
        json={'name': 'Does not matter'},
    )

    assert response.status_code == HTTPStatus.NOT_FOUND


async def test_admin_deactivate_category_success(
    app_client: AsyncClient,
    make_admin_user,
    auth_headers,
) -> None:
    admin_tokens = await make_admin_user(email='admin.deactivate@example.com')
    headers = auth_headers(admin_tokens['access_token'])

    create_response = await app_client.post(
        '/api/v1/admin/categories',
        headers=headers,
        json={'key': 'deactivate_target', 'name': 'Deactivate Target', 'sort_order': 1000},
    )
    category_id = create_response.json()['id']

    response = await app_client.delete(
        f'/api/v1/admin/categories/{category_id}',
        headers=headers,
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json()['detail'] == 'Category deactivated'


async def test_admin_upload_category_icon_success(
    app_client: AsyncClient,
    make_admin_user,
    auth_headers,
) -> None:
    admin_tokens = await make_admin_user(email='admin.icon-upload@example.com')
    headers = auth_headers(admin_tokens['access_token'])

    create_response = await app_client.post(
        '/api/v1/admin/categories',
        headers=headers,
        json={'key': 'icon_target', 'name': 'Icon Target', 'sort_order': 1000},
    )
    category_id = create_response.json()['id']

    response = await app_client.post(
        f'/api/v1/admin/categories/{category_id}/icon',
        headers=headers,
        files={'icon': ('icon.png', b'fake-png-bytes', 'image/png')},
    )

    assert response.status_code == HTTPStatus.OK

    data = response.json()

    assert data['icon_url'] is not None
    assert 'test-bucket' in data['icon_url']


async def test_admin_upload_category_icon_rejects_bad_content_type(
    app_client: AsyncClient,
    make_admin_user,
    auth_headers,
) -> None:
    admin_tokens = await make_admin_user(email='admin.icon-bad-type@example.com')
    headers = auth_headers(admin_tokens['access_token'])

    create_response = await app_client.post(
        '/api/v1/admin/categories',
        headers=headers,
        json={'key': 'icon_bad_type_target', 'name': 'Icon Bad Type Target', 'sort_order': 1000},
    )
    category_id = create_response.json()['id']

    response = await app_client.post(
        f'/api/v1/admin/categories/{category_id}/icon',
        headers=headers,
        files={'icon': ('icon.gif', b'fake-gif-bytes', 'image/gif')},
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST


async def test_admin_upload_category_icon_rejects_too_large(
    app_client: AsyncClient,
    make_admin_user,
    auth_headers,
) -> None:
    admin_tokens = await make_admin_user(email='admin.icon-too-large@example.com')
    headers = auth_headers(admin_tokens['access_token'])

    create_response = await app_client.post(
        '/api/v1/admin/categories',
        headers=headers,
        json={'key': 'icon_too_large_target', 'name': 'Icon Too Large Target', 'sort_order': 1000},
    )
    category_id = create_response.json()['id']

    oversized_content = b'0' * (2 * 1024 * 1024 + 1)

    response = await app_client.post(
        f'/api/v1/admin/categories/{category_id}/icon',
        headers=headers,
        files={'icon': ('icon.png', oversized_content, 'image/png')},
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json()['detail'] == 'Icon size must be less than 2MB'


async def test_inventory_creation_rejects_inactive_category(
    app_client: AsyncClient,
    register_user,
    make_admin_user,
    auth_headers,
    create_inventory_item,
) -> None:
    admin_tokens = await make_admin_user(email='admin.inactive-for-inventory@example.com')
    admin_headers = auth_headers(admin_tokens['access_token'])

    create_response = await app_client.post(
        '/api/v1/admin/categories',
        headers=admin_headers,
        json={'key': 'inactive_for_inventory', 'name': 'Inactive For Inventory', 'sort_order': 1000},
    )
    category_id = create_response.json()['id']

    await app_client.delete(f'/api/v1/admin/categories/{category_id}', headers=admin_headers)

    tokens = await register_user(email='inventory.inactive-category@example.com')

    response = await app_client.post(
        '/api/v1/inventory',
        headers=auth_headers(tokens['access_token']),
        json={
            'custom_name': 'Something',
            'category_id': category_id,
            'expiration_date': '2099-01-01',
        },
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json()['detail'] == 'Category is inactive'
