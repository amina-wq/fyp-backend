# Programmer Name: Rakhmatullayeva Amina
# Program Name: FoodTrack
# Description: Tests for product lookup and creation endpoints.
# First Written on: Tuesday, 14-Jul-2026
# Edited on: Tuesday, 14-Jul-2026

from http import HTTPStatus

import pytest
from httpx import AsyncClient


def _fake_off_product(barcode: str, *, name: str | None = 'Fake Milk', image_url: str | None = 'http://img/1.jpg'):
    async def _fetch(fetched_barcode: str) -> dict | None:
        if fetched_barcode != barcode:
            return None

        if name is None:
            return None

        return {
            'barcode': barcode,
            'name': name,
            'brand': 'Fake Brand',
            'tags': ['milk', 'dairy'],
            'image_url': image_url,
            'quantity': '1L',
            'source': 'off',
        }

    return _fetch


async def test_get_product_by_barcode_fetches_from_off_and_creates_product(
    app_client: AsyncClient,
    register_user,
    auth_headers,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tokens = await register_user(email='products.off-fetch@example.com')
    barcode = '1111111111111'

    monkeypatch.setattr(
        'src.modules.products.services.fetch_product_by_barcode',
        _fake_off_product(barcode),
    )

    response = await app_client.get(
        f'/api/v1/products/barcode/{barcode}',
        headers=auth_headers(tokens['access_token']),
    )

    assert response.status_code == HTTPStatus.OK

    data = response.json()

    assert data['barcode'] == barcode
    assert data['name'] == 'Fake Milk'
    assert data['source'] == 'off'
    assert data['is_verified'] is True


async def test_get_product_by_barcode_returns_404_when_off_has_no_data(
    app_client: AsyncClient,
    register_user,
    auth_headers,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tokens = await register_user(email='products.off-missing@example.com')
    barcode = '2222222222222'

    async def _fetch(_barcode: str) -> dict | None:
        return None

    monkeypatch.setattr('src.modules.products.services.fetch_product_by_barcode', _fetch)

    response = await app_client.get(
        f'/api/v1/products/barcode/{barcode}',
        headers=auth_headers(tokens['access_token']),
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json()['detail'] == 'Product not found. Try adding it manually'


async def test_get_product_by_barcode_returns_existing_without_calling_off_when_image_present(
    app_client: AsyncClient,
    register_user,
    auth_headers,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tokens = await register_user(email='products.off-cached@example.com')
    barcode = '3333333333333'

    call_count = {'n': 0}

    async def _fetch(_barcode: str) -> dict | None:
        call_count['n'] += 1
        return {
            'barcode': barcode,
            'name': 'First Fetch Milk',
            'brand': None,
            'tags': [],
            'image_url': 'http://img/first.jpg',
            'quantity': None,
            'source': 'off',
        }

    monkeypatch.setattr('src.modules.products.services.fetch_product_by_barcode', _fetch)

    first_response = await app_client.get(
        f'/api/v1/products/barcode/{barcode}',
        headers=auth_headers(tokens['access_token']),
    )

    assert first_response.status_code == HTTPStatus.OK
    assert call_count['n'] == 1

    second_response = await app_client.get(
        f'/api/v1/products/barcode/{barcode}',
        headers=auth_headers(tokens['access_token']),
    )

    assert second_response.status_code == HTTPStatus.OK
    assert call_count['n'] == 1
    assert second_response.json()['id'] == first_response.json()['id']


async def test_get_product_by_barcode_backfills_missing_image(
    app_client: AsyncClient,
    register_user,
    auth_headers,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tokens = await register_user(email='products.off-backfill@example.com')
    barcode = '4444444444444'

    call_count = {'n': 0}

    async def _fetch(_barcode: str) -> dict | None:
        call_count['n'] += 1
        return {
            'barcode': barcode,
            'name': 'Backfill Milk',
            'brand': None,
            'tags': [],
            'image_url': None if call_count['n'] == 1 else 'http://img/backfilled.jpg',
            'quantity': None,
            'source': 'off',
        }

    monkeypatch.setattr('src.modules.products.services.fetch_product_by_barcode', _fetch)

    first_response = await app_client.get(
        f'/api/v1/products/barcode/{barcode}',
        headers=auth_headers(tokens['access_token']),
    )

    assert first_response.status_code == HTTPStatus.OK
    assert first_response.json()['image_url'] is None
    assert call_count['n'] == 1

    second_response = await app_client.get(
        f'/api/v1/products/barcode/{barcode}',
        headers=auth_headers(tokens['access_token']),
    )

    assert second_response.status_code == HTTPStatus.OK
    assert second_response.json()['image_url'] == 'http://img/backfilled.jpg'
    assert call_count['n'] == 2


async def test_get_product_by_barcode_rejects_missing_token(app_client: AsyncClient) -> None:
    response = await app_client.get('/api/v1/products/barcode/1234567890123')

    assert response.status_code == HTTPStatus.UNAUTHORIZED


async def test_get_product_by_barcode_rejects_spaces_in_path(
    app_client: AsyncClient,
    register_user,
    auth_headers,
) -> None:
    tokens = await register_user(email='products.barcode-spaces@example.com')

    response = await app_client.get(
        '/api/v1/products/barcode/123 456',
        headers=auth_headers(tokens['access_token']),
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


async def test_get_product_by_id_success(
    app_client: AsyncClient,
    register_user,
    auth_headers,
) -> None:
    tokens = await register_user(email='products.get-by-id@example.com')
    headers = auth_headers(tokens['access_token'])

    create_response = await app_client.post(
        '/api/v1/products/manual',
        headers=headers,
        json={'barcode': '5555555555555', 'name': 'Manual Product For Get'},
    )
    product_id = create_response.json()['id']

    response = await app_client.get(f'/api/v1/products/{product_id}', headers=headers)

    assert response.status_code == HTTPStatus.OK
    assert response.json()['id'] == product_id


async def test_get_product_by_id_rejects_invalid_id(
    app_client: AsyncClient,
    register_user,
    auth_headers,
) -> None:
    tokens = await register_user(email='products.get-invalid-id@example.com')

    response = await app_client.get(
        '/api/v1/products/not-an-object-id',
        headers=auth_headers(tokens['access_token']),
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST


async def test_get_product_by_id_returns_404_for_nonexistent(
    app_client: AsyncClient,
    register_user,
    auth_headers,
) -> None:
    tokens = await register_user(email='products.get-404@example.com')

    response = await app_client.get(
        '/api/v1/products/507f1f77bcf86cd799439011',
        headers=auth_headers(tokens['access_token']),
    )

    assert response.status_code == HTTPStatus.NOT_FOUND


async def test_create_manual_product_success(
    app_client: AsyncClient,
    register_user,
    auth_headers,
) -> None:
    tokens = await register_user(email='products.manual-create@example.com')

    response = await app_client.post(
        '/api/v1/products/manual',
        headers=auth_headers(tokens['access_token']),
        json={
            'barcode': '6666666666666',
            'name': 'Homemade Jam',
            'brand': 'Grandma',
            'tags': ['  Sweet  ', 'HOMEMADE'],
            'quantity': '500g',
        },
    )

    assert response.status_code == HTTPStatus.CREATED

    data = response.json()

    assert data['source'] == 'manual'
    assert data['is_verified'] is False
    assert data['tags'] == ['sweet', 'homemade']


async def test_create_manual_product_rejects_missing_barcode(
    app_client: AsyncClient,
    register_user,
    auth_headers,
) -> None:
    tokens = await register_user(email='products.manual-no-barcode@example.com')

    response = await app_client.post(
        '/api/v1/products/manual',
        headers=auth_headers(tokens['access_token']),
        json={'name': 'No Barcode Product'},
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST


async def test_create_manual_product_rejects_duplicate_barcode(
    app_client: AsyncClient,
    register_user,
    auth_headers,
) -> None:
    tokens = await register_user(email='products.manual-duplicate@example.com')
    headers = auth_headers(tokens['access_token'])

    payload = {'barcode': '7777777777777', 'name': 'Duplicate Product'}

    first_response = await app_client.post('/api/v1/products/manual', headers=headers, json=payload)
    assert first_response.status_code == HTTPStatus.CREATED

    second_response = await app_client.post('/api/v1/products/manual', headers=headers, json=payload)

    assert second_response.status_code == HTTPStatus.CONFLICT


async def test_create_manual_product_rejects_barcode_with_spaces(
    app_client: AsyncClient,
    register_user,
    auth_headers,
) -> None:
    tokens = await register_user(email='products.manual-barcode-spaces@example.com')

    response = await app_client.post(
        '/api/v1/products/manual',
        headers=auth_headers(tokens['access_token']),
        json={'barcode': '123 456', 'name': 'Spaced Barcode Product'},
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


async def test_create_manual_product_rejects_missing_name(
    app_client: AsyncClient,
    register_user,
    auth_headers,
) -> None:
    tokens = await register_user(email='products.manual-no-name@example.com')

    response = await app_client.post(
        '/api/v1/products/manual',
        headers=auth_headers(tokens['access_token']),
        json={'barcode': '8888888888888'},
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
