import logging
from src.modules.auth.services import AuthService
from typing import Any
from fastapi import HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from src.core.security import validate_jwt

logger = logging.getLogger(__name__)


class JWTBearer(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)

    async def __call__(self, request: Request) -> dict[str, Any]:
        credentials: HTTPAuthorizationCredentials | None = await super().__call__(request)

        if credentials is None:
            logger.warning("Authorization failed: credentials were not provided")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authorization credentials were not provided",
            )

        if credentials.scheme.lower() != "bearer":
            logger.warning("Authorization failed: invalid authentication scheme: %s", credentials.scheme)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication scheme",
            )

        token = str(credentials.credentials)

        try:
            payload = validate_jwt(token)
        except ValueError:
            logger.warning("Authorization failed: invalid or expired token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )

        logger.info("JWT token validated successfully")

        return payload

def get_auth_service() -> AuthService:
    return AuthService()