import logging

from fastapi import APIRouter, Depends, HTTPException, status
from src.modules.auth.dependencies import get_auth_service, get_current_user
from src.modules.auth.models import User
from src.modules.auth.schemas import (
    FCMTokenUpdateSchema,
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


@router.post(
    path='/register',
    response_model=TokenResponseSchema,
    status_code=status.HTTP_201_CREATED,
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
