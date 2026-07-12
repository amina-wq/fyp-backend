import os
import uuid
from collections.abc import AsyncGenerator

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
