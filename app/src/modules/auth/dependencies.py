# Programmer Name: Rakhmatullayeva Amina
# Program Name: FoodTrack
# Description: FastAPI dependencies for extracting and validating the current authenticated user.
# First Written on: Tuesday, 26-May-2026
# Edited on: Sunday, 12-Jul-2026

import logging
from typing import Any

from beanie import PydanticObjectId
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from src.core.security import validate_jwt
from src.modules.auth.models import User, UserRole
from src.modules.auth.services import AuthService
from src.modules.auth.token_blacklist import is_token_blacklisted

logger = logging.getLogger(__name__)


class JWTBearer(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)

    async def __call__(self, request: Request) -> dict[str, Any]:
        credentials: HTTPAuthorizationCredentials | None = await super().__call__(request)

        if credentials is None:
            logger.warning('Authorization failed: credentials were not provided')
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Authorization credentials were not provided',
            )

        if credentials.scheme.lower() != 'bearer':
            logger.warning('Authorization failed: invalid authentication scheme: %s', credentials.scheme)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Invalid authentication scheme',
            )

        token = str(credentials.credentials)

        try:
            payload = validate_jwt(token, expected_type='access')
        except ValueError:
            logger.warning('Authorization failed: invalid or expired token')
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Invalid or expired token',
            )

        if await is_token_blacklisted(payload):
            logger.warning('Authorization failed: token has been revoked')

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Token has been revoked',
            )

        logger.info('JWT token validated successfully')

        return payload


jwt_bearer = JWTBearer(auto_error=False)


async def get_current_user(
    jwt_data: dict[str, Any] = Depends(jwt_bearer),
) -> User:
    user_id = jwt_data.get('sub')

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Token subject is missing',
        )

    user = await User.get(PydanticObjectId(user_id))

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='User not found',
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='User account is inactive',
        )

    return user


async def get_current_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Admin access required',
        )

    return current_user


def get_auth_service() -> AuthService:
    return AuthService()
