# Programmer Name: Rakhmatullayeva Amina
# Program Name: FoodTrack
# Description: Tests for authentication edge cases and error handling.
# First Written on: Tuesday, 14-Jul-2026
# Edited on: Tuesday, 14-Jul-2026

from http import HTTPStatus

from httpx import AsyncClient


async def test_register_rejects_duplicate_email(app_client: AsyncClient, register_user) -> None:
    email = 'duplicate.user@example.com'

    await register_user(email=email)

    response = await app_client.post(
        '/api/v1/auth/register',
        json={
            'name': 'Duplicate User',
            'email': email,
            'password': 'Password123!',
        },
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json()['detail'] == 'Email already registered'


async def test_register_rejects_invalid_email(app_client: AsyncClient) -> None:
    response = await app_client.post(
        '/api/v1/auth/register',
        json={
            'name': 'Bad Email User',
            'email': 'not-an-email',
            'password': 'Password123!',
        },
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


async def test_register_rejects_password_missing_special_char(app_client: AsyncClient) -> None:
    response = await app_client.post(
        '/api/v1/auth/register',
        json={
            'name': 'No Special User',
            'email': 'no.special@example.com',
            'password': 'Password123',
        },
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


async def test_login_rejects_nonexistent_email(app_client: AsyncClient) -> None:
    response = await app_client.post(
        '/api/v1/auth/login',
        json={
            'email': 'nobody.here@example.com',
            'password': 'Password123!',
        },
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json()['detail'] == 'Incorrect email or password'


async def test_login_rejects_wrong_password(app_client: AsyncClient, register_user) -> None:
    email = 'wrong.password@example.com'

    await register_user(email=email, password='Correct123!')

    response = await app_client.post(
        '/api/v1/auth/login',
        json={
            'email': email,
            'password': 'Incorrect123!',
        },
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json()['detail'] == 'Incorrect email or password'


async def test_login_rejects_inactive_user(app_client: AsyncClient, register_user) -> None:
    from src.modules.auth.models import User  # noqa: PLC0415

    email = 'inactive.login@example.com'
    password = 'Password123!'

    await register_user(email=email, password=password)

    user = await User.find_one(User.email == email)
    assert user is not None

    user.is_active = False
    await user.save()

    response = await app_client.post(
        '/api/v1/auth/login',
        json={'email': email, 'password': password},
    )

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert response.json()['detail'] == 'User account is inactive'


async def test_refresh_rejects_inactive_user(app_client: AsyncClient, register_user) -> None:
    from src.modules.auth.models import User  # noqa: PLC0415

    email = 'inactive.refresh@example.com'
    password = 'Password123!'

    tokens = await register_user(email=email, password=password)

    user = await User.find_one(User.email == email)
    assert user is not None

    user.is_active = False
    await user.save()

    response = await app_client.post(
        '/api/v1/auth/refresh',
        json={'refresh_token': tokens['refresh_token']},
    )

    assert response.status_code == HTTPStatus.FORBIDDEN


async def test_refresh_rejects_garbage_token(app_client: AsyncClient) -> None:
    response = await app_client.post(
        '/api/v1/auth/refresh',
        json={'refresh_token': 'this-is-not-a-jwt'},
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED


async def test_refresh_rejects_access_token_used_as_refresh(
    app_client: AsyncClient,
    register_user,
) -> None:
    tokens = await register_user(email='refresh.type-mismatch@example.com')

    response = await app_client.post(
        '/api/v1/auth/refresh',
        json={'refresh_token': tokens['access_token']},
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED


async def test_get_me_rejects_invalid_scheme(app_client: AsyncClient, register_user) -> None:
    tokens = await register_user(email='invalid.scheme@example.com')

    response = await app_client.get(
        '/api/v1/auth/me',
        headers={'Authorization': f'Token {tokens["access_token"]}'},
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED


async def test_get_me_rejects_garbage_token(app_client: AsyncClient) -> None:
    response = await app_client.get(
        '/api/v1/auth/me',
        headers={'Authorization': 'Bearer this-is-not-a-jwt'},
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED


async def test_get_me_rejects_token_of_deleted_user(app_client: AsyncClient, register_user) -> None:
    from src.modules.auth.models import User  # noqa: PLC0415

    email = 'deleted.user.me@example.com'

    tokens = await register_user(email=email)

    user = await User.find_one(User.email == email)
    assert user is not None

    await user.delete()

    response = await app_client.get(
        '/api/v1/auth/me',
        headers={'Authorization': f'Bearer {tokens["access_token"]}'},
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json()['detail'] == 'User not found'


async def test_jwt_bearer_only_routes_ignore_deleted_user(
    app_client: AsyncClient,
    register_user,
    auth_headers,
) -> None:
    from src.modules.auth.models import User  # noqa: PLC0415

    email = 'deleted.user.categories@example.com'

    tokens = await register_user(email=email)

    user = await User.find_one(User.email == email)
    assert user is not None

    await user.delete()

    response = await app_client.get(
        '/api/v1/categories',
        headers=auth_headers(tokens['access_token']),
    )

    assert response.status_code == HTTPStatus.OK


async def test_logout_rejects_invalid_scheme(app_client: AsyncClient, register_user) -> None:
    tokens = await register_user(email='logout.invalid-scheme@example.com')

    response = await app_client.post(
        '/api/v1/auth/logout',
        headers={'Authorization': f'Token {tokens["access_token"]}'},
        json={'refresh_token': tokens['refresh_token']},
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED
