# Programmer Name: Rakhmatullayeva Amina
# Program Name: FoodTrack
# Description: Redis-based request rate limiting dependency for FastAPI routes.
# First Written on: Monday, 20-Jul-2026
# Edited on: Monday, 20-Jul-2026

from collections.abc import Awaitable, Callable

from fastapi import HTTPException, Request, status
from src.core.config import settings
from src.core.redis import redis_client

RATE_LIMIT_KEY_PREFIX = 'rate_limit'

_INCREMENT_WITH_TTL_SCRIPT = """
local current = redis.call('INCR', KEYS[1])
if current == 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return current
"""

_increment_with_ttl = redis_client.register_script(_INCREMENT_WITH_TTL_SCRIPT)


def rate_limit(times: int, seconds: int, scope: str) -> Callable[[Request], Awaitable[None]]:
    async def _check(request: Request) -> None:
        if not settings.RATE_LIMIT_ENABLED:
            return

        client_host = request.client.host if request.client else 'unknown'
        key = f'{RATE_LIMIT_KEY_PREFIX}:{scope}:{client_host}'

        current = await _increment_with_ttl(keys=[key], args=[seconds])

        if current > times:
            ttl = await redis_client.ttl(key)

            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail='Too many requests. Please try again later.',
                headers={'Retry-After': str(ttl if ttl > 0 else seconds)},
            )

    return _check
