# Programmer Name: Rakhmatullayeva Amina
# Program Name: FoodTrack
# Description: Authentication and user account API endpoints.
# First Written on: Tuesday, 26-May-2026
# Edited on: Monday, 20-Jul-2026

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from src.core.rate_limiter import rate_limit
from src.modules.auth.dependencies import get_auth_service, get_current_user
from src.modules.auth.models import User
from src.modules.auth.schemas import (
    FCMTokenUpdateSchema,
    LogoutRequestSchema,
    LogoutResponseSchema,
    RefreshTokenRequestSchema,
    TokenResponseSchema,
    UserLoginSchema,
    UserRegisterSchema,
    UserResponseSchema,
    UserSettingsUpdateSchema,
    UserUpdateNameSchema,
)
from src.modules.auth.services import AuthService

logger = logging.getLogger(__name__)

router = APIRouter()

logout_bearer = HTTPBearer(auto_error=False)

register_rate_limit = rate_limit(times=5, seconds=60, scope='auth-register')
login_rate_limit = rate_limit(times=5, seconds=60, scope='auth-login')
refresh_rate_limit = rate_limit(times=10, seconds=60, scope='auth-refresh')


@router.post(
    path='/register',
    response_model=TokenResponseSchema,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(register_rate_limit)],
)
async def register_user(
    data: UserRegisterSchema,
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponseSchema:
    try:
        return await auth_service.register_user(data)
    except HTTPException:
        raise
    except Exception:
        logger.exception('Unexpected error occurred during registration')

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Unexpected error occurred during registration',
        )


@router.post(
    path='/login',
    response_model=TokenResponseSchema,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(login_rate_limit)],
)
async def login_user(
    data: UserLoginSchema,
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponseSchema:
    try:
        return await auth_service.login_user(data)
    except HTTPException:
        raise
    except Exception:
        logger.exception('Unexpected error occurred during login')

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Unexpected error occurred during login',
        )


@router.post(
    path='/refresh',
    response_model=TokenResponseSchema,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(refresh_rate_limit)],
)
async def refresh_tokens(
    data: RefreshTokenRequestSchema,
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponseSchema:
    try:
        return await auth_service.refresh_tokens(data)
    except HTTPException:
        raise
    except Exception:
        logger.exception('Unexpected error occurred during token refresh')

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Unexpected error occurred during token refresh',
        )


@router.post(
    path='/logout',
    response_model=LogoutResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def logout_user(
    data: LogoutRequestSchema,
    credentials: HTTPAuthorizationCredentials | None = Depends(logout_bearer),
    auth_service: AuthService = Depends(get_auth_service),
) -> LogoutResponseSchema:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Authorization credentials were not provided',
        )

    if credentials.scheme.lower() != 'bearer':
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid authentication scheme',
        )

    return await auth_service.logout_user(
        access_token=str(credentials.credentials),
        data=data,
    )


@router.get(
    path='/me',
    response_model=UserResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def get_me(
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> UserResponseSchema:
    return auth_service.build_user_response(current_user)


@router.patch(
    path='/me/name',
    response_model=UserResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def update_my_name(
    data: UserUpdateNameSchema,
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> UserResponseSchema:
    return await auth_service.update_user_name(
        user=current_user,
        data=data,
    )


@router.patch(
    path='/me/settings',
    response_model=UserResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def update_my_settings(
    data: UserSettingsUpdateSchema,
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> UserResponseSchema:
    return await auth_service.update_user_settings(
        user=current_user,
        data=data,
    )


@router.patch(
    path='/fcm-token',
    response_model=UserResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def update_fcm_token(
    data: FCMTokenUpdateSchema,
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> UserResponseSchema:
    return await auth_service.update_fcm_token(
        user=current_user,
        data=data,
    )
