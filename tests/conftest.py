import os
import uuid
from collections.abc import AsyncGenerator, Awaitable, Callable
from http import HTTPStatus
from typing import Any

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

TEST_DB_NAME = f'foodtrack_test_{uuid.uuid4().hex}'


os.environ.setdefault(
    'MONGODB_URL',
    'mongodb://fyp_user:fyp_password@localhost:27017/foodtrack_test?authSource=admin',
)
os.environ['MONGODB_DB_NAME'] = TEST_DB_NAME
os.environ.setdefault(
    'JWT_SECRET_KEY',
    'test_secret_key_for_foodtrack_backend_tests_32_chars_minimum',
)
os.environ.setdefault('REDIS_URL', 'redis://localhost:6379/1')
os.environ.setdefault('JWT_ALGORITHM', 'HS256')
os.environ.setdefault('JWT_ACCESS_TOKEN_EXPIRE_MINUTES', '60')
os.environ.setdefault('JWT_REFRESH_TOKEN_EXPIRE_DAYS', '7')
os.environ.setdefault('AWS_REGION', 'ap-southeast-1')
os.environ.setdefault('AWS_S3_BUCKET_NAME', 'test-bucket')
os.environ.setdefault('AWS_S3_PUBLIC_BASE_URL', 'https://example.com/test-bucket')
os.environ.setdefault('LOGGING_LEVEL', 'WARNING')

os.environ['GEMINI_API_KEY'] = ''
os.environ['SPOONACULAR_API_KEY'] = ''
os.environ['FIREBASE_CREDENTIALS_PATH'] = ''


@pytest.fixture(scope='session')
async def app_client() -> AsyncGenerator[AsyncClient, None]:
    from src.database.data_storage import db  # noqa: PLC0415
    from src.main import app  # noqa: PLC0415

    async with LifespanManager(app):
        transport = ASGITransport(app=app)

        async with AsyncClient(
            transport=transport,
            base_url='http://testserver',
        ) as client:
            yield client

        from src.core.redis import redis_client  # noqa: PLC0415

        await redis_client.flushdb()

        if db.client is not None:
            await db.client.drop_database(TEST_DB_NAME)


class FakeS3Client:
    def __init__(self) -> None:
        self.put_object_calls: list[dict[str, Any]] = []
        self.delete_object_calls: list[dict[str, Any]] = []
        self.fail_put_object = False
        self.fail_delete_object = False

    def _client_error(self, operation_name: str) -> Any:
        from botocore.exceptions import ClientError  # noqa: PLC0415

        return ClientError(
            {'Error': {'Code': 'InternalError', 'Message': 'Simulated S3 failure'}},
            operation_name,
        )

    def put_object(self, **kwargs: Any) -> dict[str, Any]:
        if self.fail_put_object:
            raise self._client_error('PutObject')

        self.put_object_calls.append(kwargs)

        return {}

    def delete_object(self, **kwargs: Any) -> dict[str, Any]:
        if self.fail_delete_object:
            raise self._client_error('DeleteObject')

        self.delete_object_calls.append(kwargs)

        return {}


@pytest.fixture(autouse=True)
def fake_s3_client(monkeypatch: pytest.MonkeyPatch) -> FakeS3Client:
    fake_client = FakeS3Client()

    def _factory(*_args: Any, **_kwargs: Any) -> FakeS3Client:
        return fake_client

    monkeypatch.setattr('src.modules.categories.services.boto3.client', _factory)
    monkeypatch.setattr('src.modules.inventory.services.boto3.client', _factory)

    return fake_client


RegisterUser = Callable[..., Awaitable[dict[str, str]]]


@pytest.fixture
def register_user(app_client: AsyncClient) -> RegisterUser:
    async def _register(
        email: str,
        password: str = 'Password123!',
        name: str = 'Test User',
    ) -> dict[str, str]:
        response = await app_client.post(
            '/api/v1/auth/register',
            json={
                'name': name,
                'email': email,
                'password': password,
            },
        )

        assert response.status_code == HTTPStatus.CREATED

        return response.json()

    return _register


@pytest.fixture
def auth_headers() -> Callable[[str], dict[str, str]]:
    def _headers(access_token: str) -> dict[str, str]:
        return {'Authorization': f'Bearer {access_token}'}

    return _headers


@pytest.fixture
def make_admin_user(
    app_client: AsyncClient,
    register_user: RegisterUser,
) -> Callable[[str], Awaitable[dict[str, str]]]:
    async def _make_admin(email: str, password: str = 'AdminPass123!') -> dict[str, str]:
        from src.modules.auth.models import User, UserRole  # noqa: PLC0415

        tokens = await register_user(email=email, password=password, name='Admin User')

        user = await User.find_one(User.email == email)
        assert user is not None

        user.role = UserRole.ADMIN
        await user.save()

        return tokens

    return _make_admin


@pytest.fixture(scope='session')
async def first_category_id(app_client: AsyncClient) -> str:
    register_response = await app_client.post(
        '/api/v1/auth/register',
        json={
            'name': 'Category Bootstrap User',
            'email': f'category.bootstrap.{uuid.uuid4().hex}@example.com',
            'password': 'Password123!',
        },
    )

    assert register_response.status_code == HTTPStatus.CREATED

    access_token = register_response.json()['access_token']

    response = await app_client.get(
        '/api/v1/categories',
        headers={'Authorization': f'Bearer {access_token}'},
    )

    assert response.status_code == HTTPStatus.OK

    categories = response.json()

    assert len(categories) > 0

    for category in categories:
        if category['key'] == 'dairy':
            return category['id']

    return categories[0]['id']


@pytest.fixture
def get_category_id_by_key(
    app_client: AsyncClient,
) -> Callable[[str, str], Awaitable[str]]:
    async def _get(key: str, access_token: str) -> str:
        response = await app_client.get(
            '/api/v1/categories',
            headers={'Authorization': f'Bearer {access_token}'},
        )

        assert response.status_code == HTTPStatus.OK

        categories = response.json()

        for category in categories:
            if category['key'] == key:
                return category['id']

        raise AssertionError(f'Category with key "{key}" not found')

    return _get


@pytest.fixture
def create_inventory_item(
    app_client: AsyncClient,
) -> Callable[..., Awaitable[dict[str, Any]]]:
    async def _create(
        access_token: str,
        category_id: str,
        **overrides: Any,
    ) -> dict[str, Any]:
        from datetime import date, timedelta  # noqa: PLC0415

        payload: dict[str, Any] = {
            'custom_name': 'Milk',
            'category_id': category_id,
            'location': 'fridge',
            'amount': 1,
            'unit': 'pcs',
            'expiration_date': (date.today() + timedelta(days=10)).isoformat(),
        }
        payload.update(overrides)

        response = await app_client.post(
            '/api/v1/inventory',
            headers={'Authorization': f'Bearer {access_token}'},
            json=payload,
        )

        assert response.status_code == HTTPStatus.CREATED

        return response.json()

    return _create
