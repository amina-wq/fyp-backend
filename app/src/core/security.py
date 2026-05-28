from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from jwt import InvalidTokenError
from pwdlib import PasswordHash
from src.core.config import settings

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hash.verify(plain_password, hashed_password)


def create_access_token(subject: str) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

    payload: dict[str, Any] = {
        'sub': subject,
        'exp': expire,
        'type': 'access',
    }

    encoded_jwt = jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    return encoded_jwt


def create_refresh_token(subject: str) -> str:
    expire = datetime.now(UTC) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)

    payload: dict[str, Any] = {
        'sub': subject,
        'exp': expire,
        'type': 'refresh',
    }

    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def validate_jwt(token: str, expected_type: str | None = None) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )

        if 'sub' not in payload:
            raise ValueError('Token subject is missing')

        if expected_type is not None and payload.get('type') != expected_type:
            raise ValueError('Invalid token type')

        return payload

    except InvalidTokenError:
        raise ValueError('Invalid or expired token')


def decode_access_token(token: str) -> dict[str, Any]:
    return validate_jwt(token)
