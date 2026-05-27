from typing import Any

from fastapi import APIRouter, Depends, status
from src.modules.auth.dependencies import JWTBearer, get_auth_service
from src.modules.auth.schemas import (
    TokenResponseSchema,
    UserLoginSchema,
    UserRegisterSchema,
)
from src.modules.auth.services import AuthService

router = APIRouter()

jwt_bearer = JWTBearer(auto_error=False)


@router.get('/protected')
async def protected_route(
    jwt_data: dict[str, Any] = Depends(jwt_bearer),
):
    return {
        'message': 'You have access',
        'jwt_data': jwt_data,
    }


@router.post(
    '/register',
    response_model=TokenResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def register_user(
    data: UserRegisterSchema,
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponseSchema:
    return await auth_service.register_user(data)


@router.post(
    '/login',
    response_model=TokenResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def login_user(
    data: UserLoginSchema,
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponseSchema:
    return await auth_service.login_user(data)
