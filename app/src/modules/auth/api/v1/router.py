from fastapi import APIRouter, Depends, HTTPException, status
from src.modules.auth.dependencies import get_auth_service, get_current_user
from src.modules.auth.models import User
from src.modules.auth.schemas import (
    RefreshTokenRequestSchema,
    TokenResponseSchema,
    UserLoginSchema,
    UserRegisterSchema,
    UserResponseSchema,
)
from src.modules.auth.services import AuthService

router = APIRouter()


def build_user_response(user: User) -> UserResponseSchema:
    return UserResponseSchema(
        id=str(user.id),
        name=user.name,
        email=user.email,
        is_active=user.is_active,
        fcm_token=user.fcm_token,
        notification_days_before=user.notification_days_before,
        account_type=user.account_type,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


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
) -> UserResponseSchema:
    return build_user_response(current_user)
