from datetime import datetime, timedelta
from http import HTTPStatus

import pytest
from httpx import AsyncClient
from src.modules.notifications.scheduling import APP_TIMEZONE
from src.modules.recipes.spoonacular_client import SpoonacularClient


def _today():
    return datetime.now(APP_TIMEZONE).date()


def _patch_find_recipes(monkeypatch: pytest.MonkeyPatch, recipes: list[dict]):
    async def _fake_find(self, ingredients: list[str], number: int = 10) -> list[dict]:
        return recipes[:number]

    monkeypatch.setattr(SpoonacularClient, 'find_recipes_by_ingredients', _fake_find)


def _patch_get_recipe_information(monkeypatch: pytest.MonkeyPatch, data: dict):
    async def _fake_details(self, recipe_id: int) -> dict:
        return data

    monkeypatch.setattr(SpoonacularClient, 'get_recipe_information', _fake_details)


async def _create_inventory_item_with_name(
    app_client: AsyncClient,
    access_token: str,
    category_id: str,
    name: str,
    amount: float = 1,
    unit: str = 'pcs',
) -> dict:
    response = await app_client.post(
        '/api/v1/inventory',
        headers={'Authorization': f'Bearer {access_token}'},
        json={
            'custom_name': name,
            'category_id': category_id,
            'amount': amount,
            'unit': unit,
            'expiration_date': (_today() + timedelta(days=10)).isoformat(),
        },
    )
    assert response.status_code == HTTPStatus.CREATED
    return response.json()


async def test_recipe_suggestions_rejects_missing_token(app_client: AsyncClient) -> None:
    response = await app_client.post('/api/v1/recipes/by-ingredients', json={'number': 5})

    assert response.status_code == HTTPStatus.UNAUTHORIZED


async def test_recipe_suggestions_rejects_number_out_of_range(
    app_client: AsyncClient,
    register_user,
    auth_headers,
) -> None:
    tokens = await register_user(email='recipes.number-range@example.com')

    response = await app_client.post(
        '/api/v1/recipes/by-ingredients',
        headers=auth_headers(tokens['access_token']),
        json={'number': 21},
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


async def test_recipe_suggestions_returns_empty_when_no_inventory(
    app_client: AsyncClient,
    register_user,
    auth_headers,
) -> None:
    tokens = await register_user(email='recipes.no-inventory@example.com')

    response = await app_client.post(
        '/api/v1/recipes/by-ingredients',
        headers=auth_headers(tokens['access_token']),
        json={'number': 5},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == []


async def test_recipe_suggestions_success_with_mocked_spoonacular(
    app_client: AsyncClient,
    register_user,
    auth_headers,
    first_category_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tokens = await register_user(email='recipes.suggestions-success@example.com')
    access_token = tokens['access_token']

    await _create_inventory_item_with_name(app_client, access_token, first_category_id, 'Milk')

    _patch_find_recipes(
        monkeypatch,
        [
            {
                'id': 555001,
                'title': 'Milk Pancakes',
                'image': 'http://img/pancakes.jpg',
                'usedIngredients': [{'id': 1, 'name': 'milk'}],
                'missedIngredients': [{'id': 2, 'name': 'flour'}],
                'unusedIngredients': [],
            },
        ],
    )

    response = await app_client.post(
        '/api/v1/recipes/by-ingredients',
        headers=auth_headers(access_token),
        json={'number': 5},
    )

    assert response.status_code == HTTPStatus.OK

    data = response.json()

    assert len(data) == 1
    assert data[0]['spoonacular_id'] == 555001
    assert data[0]['title'] == 'Milk Pancakes'
    assert data[0]['used_ingredient_count'] == 1
    assert data[0]['missed_ingredient_count'] == 1
    assert data[0]['match_score'] == 50.0


async def test_recipe_suggestions_uses_cache_on_second_call(
    app_client: AsyncClient,
    register_user,
    auth_headers,
    first_category_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tokens = await register_user(email='recipes.suggestions-cache@example.com')
    access_token = tokens['access_token']

    await _create_inventory_item_with_name(app_client, access_token, first_category_id, 'Chicken')

    call_count = {'n': 0}

    async def _fake_find(self, ingredients: list[str], number: int = 10) -> list[dict]:
        call_count['n'] += 1
        return [
            {
                'id': 555002,
                'title': 'Chicken Soup',
                'image': None,
                'usedIngredients': [{'id': 1, 'name': 'chicken'}],
                'missedIngredients': [],
                'unusedIngredients': [],
            },
        ]

    monkeypatch.setattr(SpoonacularClient, 'find_recipes_by_ingredients', _fake_find)

    first_response = await app_client.post(
        '/api/v1/recipes/by-ingredients',
        headers=auth_headers(access_token),
        json={'number': 1},
    )
    assert first_response.status_code == HTTPStatus.OK
    assert call_count['n'] == 1

    second_response = await app_client.post(
        '/api/v1/recipes/by-ingredients',
        headers=auth_headers(access_token),
        json={'number': 1},
    )
    assert second_response.status_code == HTTPStatus.OK
    assert call_count['n'] == 1
    assert second_response.json()[0]['spoonacular_id'] == 555002


async def test_get_recipe_details_returns_404_when_never_searched(
    app_client: AsyncClient,
    register_user,
    auth_headers,
) -> None:
    tokens = await register_user(email='recipes.details-404@example.com')

    response = await app_client.get(
        '/api/v1/recipes/999999',
        headers=auth_headers(tokens['access_token']),
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json()['detail'] == 'Recipe not found. Search recipes first.'


async def test_get_recipe_details_rejects_invalid_id(
    app_client: AsyncClient,
    register_user,
    auth_headers,
) -> None:
    tokens = await register_user(email='recipes.details-invalid-id@example.com')

    response = await app_client.get(
        '/api/v1/recipes/0',
        headers=auth_headers(tokens['access_token']),
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


async def test_get_recipe_details_success_with_availability(
    app_client: AsyncClient,
    register_user,
    auth_headers,
    first_category_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tokens = await register_user(email='recipes.details-success@example.com')
    access_token = tokens['access_token']

    await _create_inventory_item_with_name(
        app_client,
        access_token,
        first_category_id,
        'Kefir',
        amount=1,
        unit='l',
    )

    _patch_find_recipes(
        monkeypatch,
        [
            {
                'id': 555003,
                'title': 'Kefir Shake',
                'image': None,
                'usedIngredients': [{'id': 1, 'name': 'kefir'}],
                'missedIngredients': [{'id': 2, 'name': 'sugar'}],
                'unusedIngredients': [],
            },
        ],
    )

    search_response = await app_client.post(
        '/api/v1/recipes/by-ingredients',
        headers=auth_headers(access_token),
        json={'number': 1},
    )
    assert search_response.status_code == HTTPStatus.OK

    _patch_get_recipe_information(
        monkeypatch,
        {
            'readyInMinutes': 15,
            'servings': 2,
            'nutrition': {'nutrients': [{'name': 'Calories', 'amount': 300}]},
            'extendedIngredients': [
                {'id': 1, 'nameClean': 'kefir', 'amount': 200, 'unit': 'ml'},
                {'id': 2, 'nameClean': 'sugar', 'amount': 50, 'unit': 'g'},
            ],
            'analyzedInstructions': [
                {'steps': [{'number': 1, 'step': 'Mix everything.'}]},
            ],
        },
    )

    detail_response = await app_client.get(
        f'/api/v1/recipes/{555003}',
        headers=auth_headers(access_token),
    )

    assert detail_response.status_code == HTTPStatus.OK

    data = detail_response.json()

    assert data['ready_in_minutes'] == 15
    assert data['servings'] == 2
    assert data['calories'] == 300
    assert len(data['steps']) == 1
    assert data['steps'][0]['step'] == 'Mix everything.'

    ingredient_names = {ingredient['name']: ingredient for ingredient in data['ingredients']}

    assert ingredient_names['kefir']['availability_status'] == 'available'
    assert ingredient_names['sugar']['availability_status'] == 'missing'


async def test_get_recipe_details_skips_spoonacular_call_when_already_fetched(
    app_client: AsyncClient,
    register_user,
    auth_headers,
    first_category_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tokens = await register_user(email='recipes.details-cache@example.com')
    access_token = tokens['access_token']

    await _create_inventory_item_with_name(app_client, access_token, first_category_id, 'Egg')

    _patch_find_recipes(
        monkeypatch,
        [
            {
                'id': 555004,
                'title': 'Egg Toast',
                'image': None,
                'usedIngredients': [{'id': 1, 'name': 'egg'}],
                'missedIngredients': [],
                'unusedIngredients': [],
            },
        ],
    )

    await app_client.post(
        '/api/v1/recipes/by-ingredients',
        headers=auth_headers(access_token),
        json={'number': 1},
    )

    call_count = {'n': 0}

    async def _fake_details(self, recipe_id: int) -> dict:
        call_count['n'] += 1
        return {
            'readyInMinutes': 5,
            'servings': 1,
            'nutrition': {'nutrients': []},
            'extendedIngredients': [],
            'analyzedInstructions': [],
        }

    monkeypatch.setattr(SpoonacularClient, 'get_recipe_information', _fake_details)

    first_response = await app_client.get(f'/api/v1/recipes/{555004}', headers=auth_headers(access_token))
    assert first_response.status_code == HTTPStatus.OK
    assert call_count['n'] == 1

    second_response = await app_client.get(f'/api/v1/recipes/{555004}', headers=auth_headers(access_token))
    assert second_response.status_code == HTTPStatus.OK
    assert call_count['n'] == 1
