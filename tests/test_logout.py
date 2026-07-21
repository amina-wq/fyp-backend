# Programmer Name: Rakhmatullayeva Amina
# Program Name: FoodTrack
# Description: Tests for the logout and token revocation flow.
# First Written on: Sunday, 12-Jul-2026
# Edited on: Sunday, 12-Jul-2026

from http import HTTPStatus

from httpx import AsyncClient


async def _register_user(
    app_client: AsyncClient,
    email: str,
    password: str = 'Logout123!',
) -> dict[str, str]:
    response = await app_client.post(
        '/api/v1/auth/register',
        json={
            'name': 'Logout User',
            'email': email,
            'password': password,
        },
    )

    assert response.status_code == HTTPStatus.CREATED

    return response.json()


def _auth_headers(access_token: str) -> dict[str, str]:
    return {
        'Authorization': f'Bearer {access_token}',
    }


async def test_logout_success(app_client: AsyncClient) -> None:
    tokens = await _register_user(
        app_client=app_client,
        email='logout.success@example.com',
    )

    response = await app_client.post(
        '/api/v1/auth/logout',
        headers=_auth_headers(tokens['access_token']),
        json={
            'refresh_token': tokens['refresh_token'],
        },
    )

    assert response.status_code == HTTPStatus.OK

    data = response.json()

    assert data['detail'] == 'Logged out successfully'


async def test_logout_revokes_access_token(app_client: AsyncClient) -> None:
    tokens = await _register_user(
        app_client=app_client,
        email='logout.access@example.com',
    )

    logout_response = await app_client.post(
        '/api/v1/auth/logout',
        headers=_auth_headers(tokens['access_token']),
        json={
            'refresh_token': tokens['refresh_token'],
        },
    )

    assert logout_response.status_code == HTTPStatus.OK

    me_response = await app_client.get(
        '/api/v1/auth/me',
        headers=_auth_headers(tokens['access_token']),
    )

    assert me_response.status_code == HTTPStatus.UNAUTHORIZED


async def test_logout_revokes_refresh_token(app_client: AsyncClient) -> None:
    tokens = await _register_user(
        app_client=app_client,
        email='logout.refresh@example.com',
    )

    logout_response = await app_client.post(
        '/api/v1/auth/logout',
        headers=_auth_headers(tokens['access_token']),
        json={
            'refresh_token': tokens['refresh_token'],
        },
    )

    assert logout_response.status_code == HTTPStatus.OK

    refresh_response = await app_client.post(
        '/api/v1/auth/refresh',
        json={
            'refresh_token': tokens['refresh_token'],
        },
    )

    assert refresh_response.status_code == HTTPStatus.UNAUTHORIZED


async def test_logout_rejects_missing_access_token(app_client: AsyncClient) -> None:
    tokens = await _register_user(
        app_client=app_client,
        email='logout.missing-access@example.com',
    )

    response = await app_client.post(
        '/api/v1/auth/logout',
        json={
            'refresh_token': tokens['refresh_token'],
        },
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED


async def test_logout_rejects_mismatched_refresh_token(app_client: AsyncClient) -> None:
    first_user_tokens = await _register_user(
        app_client=app_client,
        email='logout.first@example.com',
    )
    second_user_tokens = await _register_user(
        app_client=app_client,
        email='logout.second@example.com',
    )

    response = await app_client.post(
        '/api/v1/auth/logout',
        headers=_auth_headers(first_user_tokens['access_token']),
        json={
            'refresh_token': second_user_tokens['refresh_token'],
        },
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED


async def test_login_after_logout_returns_new_working_tokens(
    app_client: AsyncClient,
) -> None:
    email = 'logout.login-again@example.com'
    password = 'Logout123!'

    tokens = await _register_user(
        app_client=app_client,
        email=email,
        password=password,
    )

    logout_response = await app_client.post(
        '/api/v1/auth/logout',
        headers=_auth_headers(tokens['access_token']),
        json={
            'refresh_token': tokens['refresh_token'],
        },
    )

    assert logout_response.status_code == HTTPStatus.OK

    login_response = await app_client.post(
        '/api/v1/auth/login',
        json={
            'email': email,
            'password': password,
        },
    )

    assert login_response.status_code == HTTPStatus.OK

    new_tokens = login_response.json()

    me_response = await app_client.get(
        '/api/v1/auth/me',
        headers=_auth_headers(new_tokens['access_token']),
    )

    assert me_response.status_code == HTTPStatus.OK
