# Programmer Name: Rakhmatullayeva Amina
# Program Name: FoodTrack
# Description: Tests for user registration and login endpoints.
# First Written on: Sunday, 12-Jul-2026
# Edited on: Sunday, 12-Jul-2026

from http import HTTPStatus

from httpx import AsyncClient


async def test_register_user_success(app_client: AsyncClient) -> None:
    response = await app_client.post(
        '/api/v1/auth/register',
        json={
            'name': 'Test User',
            'email': 'test.user@example.com',
            'password': 'Test123!',
        },
    )

    assert response.status_code == HTTPStatus.CREATED

    data = response.json()

    assert 'access_token' in data
    assert 'refresh_token' in data


async def test_register_user_rejects_weak_password(app_client: AsyncClient) -> None:
    response = await app_client.post(
        '/api/v1/auth/register',
        json={
            'name': 'Weak User',
            'email': 'weak.user@example.com',
            'password': 'password',
        },
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


async def test_login_user_success(app_client: AsyncClient) -> None:
    email = 'login.user@example.com'
    password = 'Login123!'

    await app_client.post(
        '/api/v1/auth/register',
        json={
            'name': 'Login User',
            'email': email,
            'password': password,
        },
    )

    response = await app_client.post(
        '/api/v1/auth/login',
        json={
            'email': email,
            'password': password,
        },
    )

    assert response.status_code == HTTPStatus.OK

    data = response.json()

    assert 'access_token' in data
    assert 'refresh_token' in data


async def test_get_me_with_valid_access_token(app_client: AsyncClient) -> None:
    email = 'me.user@example.com'
    password = 'User123!'

    register_response = await app_client.post(
        '/api/v1/auth/register',
        json={
            'name': 'Me User',
            'email': email,
            'password': password,
        },
    )

    access_token = register_response.json()['access_token']

    response = await app_client.get(
        '/api/v1/auth/me',
        headers={
            'Authorization': f'Bearer {access_token}',
        },
    )

    assert response.status_code == HTTPStatus.OK

    data = response.json()

    assert data['email'] == email
    assert data['name'] == 'Me User'


async def test_get_me_rejects_missing_token(app_client: AsyncClient) -> None:
    response = await app_client.get('/api/v1/auth/me')

    assert response.status_code == HTTPStatus.UNAUTHORIZED


async def test_refresh_token_success(app_client: AsyncClient) -> None:
    register_response = await app_client.post(
        '/api/v1/auth/register',
        json={
            'name': 'Refresh User',
            'email': 'refresh.user@example.com',
            'password': 'Refresh123!',
        },
    )

    refresh_token = register_response.json()['refresh_token']

    response = await app_client.post(
        '/api/v1/auth/refresh',
        json={
            'refresh_token': refresh_token,
        },
    )

    assert response.status_code == HTTPStatus.OK

    data = response.json()

    assert 'access_token' in data
    assert 'refresh_token' in data


async def test_protected_endpoint_rejects_refresh_token_as_bearer(app_client: AsyncClient) -> None:
    register_response = await app_client.post(
        '/api/v1/auth/register',
        json={
            'name': 'Refresh Bearer User',
            'email': 'refresh.bearer@example.com',
            'password': 'Bearer123!',
        },
    )

    refresh_token = register_response.json()['refresh_token']

    response = await app_client.get(
        '/api/v1/auth/me',
        headers={
            'Authorization': f'Bearer {refresh_token}',
        },
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED
