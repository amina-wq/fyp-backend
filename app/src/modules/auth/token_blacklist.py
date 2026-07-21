# Programmer Name: Rakhmatullayeva Amina
# Program Name: FoodTrack
# Description: Redis-backed blacklist for revoked JWT tokens.
# First Written on: Sunday, 12-Jul-2026
# Edited on: Sunday, 12-Jul-2026

from datetime import UTC, datetime
from typing import Any

from src.core.redis import redis_client

TOKEN_BLACKLIST_PREFIX = 'token_blacklist'


def _build_blacklist_key(jti: str) -> str:
    return f'{TOKEN_BLACKLIST_PREFIX}:{jti}'


def _get_token_ttl_seconds(payload: dict[str, Any]) -> int:
    expires_at = payload.get('exp')

    if not expires_at:
        return 0

    if isinstance(expires_at, datetime):
        expires_at_datetime = expires_at
    else:
        expires_at_datetime = datetime.fromtimestamp(
            int(expires_at),
            tz=UTC,
        )

    ttl_seconds = int((expires_at_datetime - datetime.now(UTC)).total_seconds())

    return max(ttl_seconds, 0)


async def blacklist_token(payload: dict[str, Any]) -> None:
    jti = payload.get('jti')

    if not jti:
        return

    ttl_seconds = _get_token_ttl_seconds(payload)

    if ttl_seconds <= 0:
        return

    await redis_client.setex(
        name=_build_blacklist_key(jti),
        time=ttl_seconds,
        value='1',
    )


async def is_token_blacklisted(payload: dict[str, Any]) -> bool:
    jti = payload.get('jti')

    if not jti:
        return False

    result = await redis_client.exists(_build_blacklist_key(jti))

    return result == 1
