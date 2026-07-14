from http import HTTPStatus

from httpx import AsyncClient


async def test_get_categories_rejects_missing_token(app_client: AsyncClient) -> None:
    response = await app_client.get('/api/v1/categories')

    assert response.status_code == HTTPStatus.UNAUTHORIZED


async def test_get_categories_returns_only_active_sorted_by_sort_order(
    app_client: AsyncClient,
    register_user,
    auth_headers,
) -> None:
    tokens = await register_user(email='categories.list@example.com')

    response = await app_client.get(
        '/api/v1/categories',
        headers=auth_headers(tokens['access_token']),
    )

    assert response.status_code == HTTPStatus.OK

    categories = response.json()

    assert len(categories) >= 15
    assert all(category['is_active'] for category in categories)

    sort_orders = [category['sort_order'] for category in categories]

    assert sort_orders == sorted(sort_orders)

    keys_in_order = [category['key'] for category in categories]

    assert keys_in_order.index('dairy') < keys_in_order.index('meat')
    assert keys_in_order.index('meat') < keys_in_order.index('other')


async def test_get_category_by_id_success(
    app_client: AsyncClient,
    register_user,
    auth_headers,
    first_category_id: str,
) -> None:
    tokens = await register_user(email='categories.get-by-id@example.com')

    response = await app_client.get(
        f'/api/v1/categories/{first_category_id}',
        headers=auth_headers(tokens['access_token']),
    )

    assert response.status_code == HTTPStatus.OK

    data = response.json()

    assert data['id'] == first_category_id
    assert data['key'] == 'dairy'


async def test_get_category_by_id_rejects_invalid_id(
    app_client: AsyncClient,
    register_user,
    auth_headers,
) -> None:
    tokens = await register_user(email='categories.invalid-id@example.com')

    response = await app_client.get(
        '/api/v1/categories/not-a-valid-object-id',
        headers=auth_headers(tokens['access_token']),
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST


async def test_get_category_by_id_returns_404_for_nonexistent_id(
    app_client: AsyncClient,
    register_user,
    auth_headers,
) -> None:
    tokens = await register_user(email='categories.nonexistent@example.com')

    response = await app_client.get(
        '/api/v1/categories/507f1f77bcf86cd799439011',
        headers=auth_headers(tokens['access_token']),
    )

    assert response.status_code == HTTPStatus.NOT_FOUND


async def test_get_category_by_id_returns_404_for_inactive_category(
    app_client: AsyncClient,
    register_user,
    auth_headers,
    make_admin_user,
) -> None:
    admin_tokens = await make_admin_user(email='categories.deactivate-admin@example.com')

    create_response = await app_client.post(
        '/api/v1/admin/categories',
        headers=auth_headers(admin_tokens['access_token']),
        json={'key': 'to be deactivated', 'name': 'To Be Deactivated'},
    )

    assert create_response.status_code == HTTPStatus.CREATED

    category_id = create_response.json()['id']

    delete_response = await app_client.delete(
        f'/api/v1/admin/categories/{category_id}',
        headers=auth_headers(admin_tokens['access_token']),
    )

    assert delete_response.status_code == HTTPStatus.OK

    tokens = await register_user(email='categories.see-inactive@example.com')

    response = await app_client.get(
        f'/api/v1/categories/{category_id}',
        headers=auth_headers(tokens['access_token']),
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
