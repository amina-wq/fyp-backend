from beanie import PydanticObjectId
from fastapi import HTTPException, status
from src.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    validate_jwt,
    verify_password,
)
from src.modules.auth.models import User
from src.modules.auth.schemas import (
    RefreshTokenRequestSchema,
    TokenResponseSchema,
    UserLoginSchema,
    UserRegisterSchema,
)


class AuthService:
    def _create_tokens(self, user: User) -> TokenResponseSchema:
        access_token = create_access_token(subject=str(user.id))
        refresh_token = create_refresh_token(subject=str(user.id))

        return TokenResponseSchema(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type='bearer',
        )

    async def register_user(self, data: UserRegisterSchema) -> TokenResponseSchema:
        existing_user = await User.find_one(User.email == data.email)

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Email already registered',
            )

        user = User(
            name=data.name,
            email=data.email,
            hashed_password=hash_password(data.password),
        )

        await user.insert()

        return self._create_tokens(user)

    async def login_user(self, data: UserLoginSchema) -> TokenResponseSchema:
        user = await User.find_one(User.email == data.email)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Incorrect email or password',
            )

        if not verify_password(data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Incorrect email or password',
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='User account is inactive',
            )

        return self._create_tokens(user)

    async def refresh_tokens(self, data: RefreshTokenRequestSchema) -> TokenResponseSchema:
        try:
            payload = validate_jwt(data.refresh_token, expected_type='refresh')
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Invalid or expired refresh token',
            )

        user_id = payload['sub']

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

        return self._create_tokens(user)
