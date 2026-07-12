from redis.asyncio import Redis
from src.core.config import settings

redis_client = Redis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
)


async def close_redis_client() -> None:
    await redis_client.aclose()
