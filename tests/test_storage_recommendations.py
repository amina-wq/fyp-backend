from http import HTTPStatus

import pytest
from httpx import AsyncClient
from src.modules.storage_recommendations.gemini_client import GeminiStorageClient


def _patch_gemini(monkeypatch: pytest.MonkeyPatch, ai_data: dict | None):
    async def _fake_fetch(self, name: str, category, location, state) -> dict | None:
        return ai_data

    monkeypatch.setattr(GeminiStorageClient, 'fetch_storage_recommendation', _fake_fetch)


def _basic_ai_data(canonical_name: str = 'milk') -> dict:
    return {
        'canonical_name': canonical_name,
        'display_name': canonical_name.title(),
        'category': 'dairy',
        'aliases': ['whole milk'],
        'rules': [
            {
                'location': 'fridge',
                'state': 'unopened',
                'recommended_days': 7,
                'min_days': 5,
                'max_days': 10,
                'is_default': True,
            },
            {
                'location': 'fridge',
                'state': 'opened',
                'recommended_days': 3,
                'min_days': 2,
                'max_days': 5,
                'is_default': False,
            },
            {
                'location': 'freezer',
                'state': 'unopened',
                'recommended_days': 90,
                'min_days': 60,
                'max_days': 120,
                'is_default': False,
            },
        ],
        'confidence': 0.85,
    }


async def test_get_recommendation_rejects_missing_token(app_client: AsyncClient) -> None:
    response = await app_client.post(
        '/api/v1/storage/recommendations',
        json={'name': 'Milk'},
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED


async def test_get_recommendation_rejects_invalid_name(
    app_client: AsyncClient,
    register_user,
    auth_headers,
) -> None:
    tokens = await register_user(email='storage.invalid-name@example.com')

    response = await app_client.post(
        '/api/v1/storage/recommendations',
        headers=auth_headers(tokens['access_token']),
        json={'name': '123 kg'},
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert response.json()['detail'] == 'Product name is invalid'


async def test_get_recommendation_returns_404_when_gemini_has_no_data(
    app_client: AsyncClient,
    register_user,
    auth_headers,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tokens = await register_user(email='storage.no-gemini-data@example.com')

    _patch_gemini(monkeypatch, None)

    response = await app_client.post(
        '/api/v1/storage/recommendations',
        headers=auth_headers(tokens['access_token']),
        json={'name': 'Some Unknown Product Xyz'},
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json()['detail'] == 'Storage recommendation not found'


async def test_get_recommendation_success_default_rule(
    app_client: AsyncClient,
    register_user,
    auth_headers,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tokens = await register_user(email='storage.success-default@example.com')

    _patch_gemini(monkeypatch, _basic_ai_data('storage milk one'))

    response = await app_client.post(
        '/api/v1/storage/recommendations',
        headers=auth_headers(tokens['access_token']),
        json={'name': 'Storage Milk One'},
    )

    assert response.status_code == HTTPStatus.OK

    data = response.json()

    assert data['canonical_name'] == 'storage milk one'
    assert data['category'] == 'dairy'
    assert data['recommended_days'] == 7
    assert data['location'] == 'fridge'
    assert data['state'] == 'unopened'
    assert data['requires_clarification'] is False
    assert len(data['options']) == 3


async def test_get_recommendation_uses_cache_on_second_call(
    app_client: AsyncClient,
    register_user,
    auth_headers,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tokens = await register_user(email='storage.cache@example.com')
    headers = auth_headers(tokens['access_token'])

    call_count = {'n': 0}

    async def _fake_fetch(self, name, category, location, state) -> dict | None:
        call_count['n'] += 1
        return _basic_ai_data('storage cache product')

    monkeypatch.setattr(GeminiStorageClient, 'fetch_storage_recommendation', _fake_fetch)

    first_response = await app_client.post(
        '/api/v1/storage/recommendations',
        headers=headers,
        json={'name': 'Storage Cache Product'},
    )
    assert first_response.status_code == HTTPStatus.OK
    assert call_count['n'] == 1

    second_response = await app_client.post(
        '/api/v1/storage/recommendations',
        headers=headers,
        json={'name': 'Storage Cache Product'},
    )
    assert second_response.status_code == HTTPStatus.OK
    assert call_count['n'] == 1


async def test_get_recommendation_selects_rule_by_location_and_state(
    app_client: AsyncClient,
    register_user,
    auth_headers,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tokens = await register_user(email='storage.select-exact@example.com')
    headers = auth_headers(tokens['access_token'])

    _patch_gemini(monkeypatch, _basic_ai_data('storage select exact'))

    await app_client.post(
        '/api/v1/storage/recommendations',
        headers=headers,
        json={'name': 'Storage Select Exact'},
    )

    response = await app_client.post(
        '/api/v1/storage/recommendations',
        headers=headers,
        json={'name': 'Storage Select Exact', 'location': 'freezer', 'state': 'unopened'},
    )

    assert response.status_code == HTTPStatus.OK

    data = response.json()

    assert data['location'] == 'freezer'
    assert data['recommended_days'] == 90


async def test_get_recommendation_selects_default_rule_for_location_only(
    app_client: AsyncClient,
    register_user,
    auth_headers,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tokens = await register_user(email='storage.select-location-only@example.com')
    headers = auth_headers(tokens['access_token'])

    _patch_gemini(monkeypatch, _basic_ai_data('storage select location'))

    await app_client.post(
        '/api/v1/storage/recommendations',
        headers=headers,
        json={'name': 'Storage Select Location'},
    )

    response = await app_client.post(
        '/api/v1/storage/recommendations',
        headers=headers,
        json={'name': 'Storage Select Location', 'location': 'fridge'},
    )

    assert response.status_code == HTTPStatus.OK

    data = response.json()

    assert data['location'] == 'fridge'
    assert data['state'] == 'unopened'
    assert data['recommended_days'] == 7


async def test_get_recommendation_requires_clarification_when_flagged(
    app_client: AsyncClient,
    register_user,
    auth_headers,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from datetime import UTC, datetime  # noqa: PLC0415

    from src.modules.storage_recommendations.models import StorageRecommendation  # noqa: PLC0415

    tokens = await register_user(email='storage.requires-clarification@example.com')

    document = StorageRecommendation(
        canonical_name='ambiguous product',
        display_name='Ambiguous Product',
        category='other',
        aliases=['ambiguous product'],
        normalized_aliases=['ambiguous product'],
        rules=[
            {
                'location': 'fridge',
                'state': 'unopened',
                'recommended_days': 5,
                'is_default': True,
            },
            {
                'location': 'pantry',
                'state': 'unopened',
                'recommended_days': 10,
                'is_default': False,
            },
        ],
        source='gemini',
        is_verified=False,
        confidence=0.4,
        requires_clarification=True,
        updated_at=datetime.now(UTC),
    )
    await document.insert()

    response = await app_client.post(
        '/api/v1/storage/recommendations',
        headers=auth_headers(tokens['access_token']),
        json={'name': 'Ambiguous Product'},
    )

    assert response.status_code == HTTPStatus.OK

    data = response.json()

    assert data['requires_clarification'] is True
    assert data['recommended_days'] is None
    assert data['location'] is None
    assert len(data['options']) == 2


async def test_get_recommendation_clarification_suppressed_when_location_given(
    app_client: AsyncClient,
    register_user,
    auth_headers,
) -> None:
    from datetime import UTC, datetime  # noqa: PLC0415

    from src.modules.storage_recommendations.models import StorageRecommendation  # noqa: PLC0415

    tokens = await register_user(email='storage.clarification-suppressed@example.com')

    document = StorageRecommendation(
        canonical_name='ambiguous product two',
        display_name='Ambiguous Product Two',
        category='other',
        aliases=['ambiguous product two'],
        normalized_aliases=['ambiguous product two'],
        rules=[
            {
                'location': 'fridge',
                'state': 'unopened',
                'recommended_days': 5,
                'is_default': True,
            },
            {
                'location': 'pantry',
                'state': 'unopened',
                'recommended_days': 10,
                'is_default': False,
            },
        ],
        source='gemini',
        is_verified=False,
        confidence=0.4,
        requires_clarification=True,
        updated_at=datetime.now(UTC),
    )
    await document.insert()

    response = await app_client.post(
        '/api/v1/storage/recommendations',
        headers=auth_headers(tokens['access_token']),
        json={'name': 'Ambiguous Product Two', 'location': 'pantry'},
    )

    assert response.status_code == HTTPStatus.OK

    data = response.json()

    assert data['requires_clarification'] is False
    assert data['recommended_days'] == 10
    assert data['location'] == 'pantry'


async def test_get_recommendation_returns_404_when_all_rules_invalid(
    app_client: AsyncClient,
    register_user,
    auth_headers,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tokens = await register_user(email='storage.all-rules-invalid@example.com')

    ai_data = {
        'canonical_name': 'broken rules product',
        'display_name': 'Broken Rules Product',
        'category': 'dairy',
        'aliases': [],
        'rules': [
            {
                'location': 'fridge',
                'state': 'unopened',
                'recommended_days': 5,
                'min_days': 10,
                'max_days': 2,
                'is_default': True,
            },
        ],
        'confidence': 0.5,
    }

    _patch_gemini(monkeypatch, ai_data)

    response = await app_client.post(
        '/api/v1/storage/recommendations',
        headers=auth_headers(tokens['access_token']),
        json={'name': 'Broken Rules Product'},
    )

    assert response.status_code == HTTPStatus.NOT_FOUND


async def test_get_recommendation_coerces_unknown_category_to_other(
    app_client: AsyncClient,
    register_user,
    auth_headers,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tokens = await register_user(email='storage.unknown-category@example.com')

    ai_data = _basic_ai_data('storage unknown category product')
    ai_data['category'] = 'not-a-real-category'

    _patch_gemini(monkeypatch, ai_data)

    response = await app_client.post(
        '/api/v1/storage/recommendations',
        headers=auth_headers(tokens['access_token']),
        json={'name': 'Storage Unknown Category Product'},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json()['category'] == 'other'


async def test_get_recommendation_rejects_missing_name(
    app_client: AsyncClient,
    register_user,
    auth_headers,
) -> None:
    tokens = await register_user(email='storage.missing-name@example.com')

    response = await app_client.post(
        '/api/v1/storage/recommendations',
        headers=auth_headers(tokens['access_token']),
        json={},
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
