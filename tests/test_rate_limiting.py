from http import HTTPStatus

import pytest
from httpx import AsyncClient
from src.core.config import settings
from src.core.redis import redis_client


async def _clear_rate_limit_keys(scope: str) -> None:
    keys = await redis_client.keys(f'rate_limit:{scope}:*')

    if keys:
        await redis_client.delete(*keys)


async def test_login_is_rate_limited_per_ip(
    app_client: AsyncClient,
    register_user,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    email = 'rate.limit.login@example.com'
    password = 'Password123!'

    await register_user(email=email, password=password)

    await _clear_rate_limit_keys('auth-login')

    monkeypatch.setattr(settings, 'RATE_LIMIT_ENABLED', True)

    for _ in range(5):
        response = await app_client.post(
            '/api/v1/auth/login',
            json={'email': email, 'password': password},
        )

        assert response.status_code == HTTPStatus.OK

    blocked_response = await app_client.post(
        '/api/v1/auth/login',
        json={'email': email, 'password': password},
    )

    assert blocked_response.status_code == HTTPStatus.TOO_MANY_REQUESTS
    assert 'Retry-After' in blocked_response.headers

    await _clear_rate_limit_keys('auth-login')


async def test_register_is_rate_limited_per_ip(
    app_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await _clear_rate_limit_keys('auth-register')

    monkeypatch.setattr(settings, 'RATE_LIMIT_ENABLED', True)

    for i in range(5):
        response = await app_client.post(
            '/api/v1/auth/register',
            json={
                'name': 'Rate Limit User',
                'email': f'rate.limit.register.{i}@example.com',
                'password': 'Password123!',
            },
        )

        assert response.status_code == HTTPStatus.CREATED

    blocked_response = await app_client.post(
        '/api/v1/auth/register',
        json={
            'name': 'Rate Limit User',
            'email': 'rate.limit.register.overflow@example.com',
            'password': 'Password123!',
        },
    )

    assert blocked_response.status_code == HTTPStatus.TOO_MANY_REQUESTS

    await _clear_rate_limit_keys('auth-register')
