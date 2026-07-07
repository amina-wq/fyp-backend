from datetime import UTC, datetime

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
    FCMTokenUpdateSchema,
    RefreshTokenRequestSchema,
    TokenResponseSchema,
    UserLoginSchema,
    UserRegisterSchema,
    UserResponseSchema,
    UserSettingsUpdateSchema,
    UserUpdateNameSchema,
)


class AuthService:
    @classmethod
    def _create_tokens(cls, user: User) -> TokenResponseSchema:
        access_token = create_access_token(subject=str(user.id))
        refresh_token = create_refresh_token(subject=str(user.id))

        return TokenResponseSchema(
            access_token=access_token,
            refresh_token=refresh_token,
        )

    @classmethod
    async def register_user(cls, data: UserRegisterSchema) -> TokenResponseSchema:
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

        return cls._create_tokens(user)

    @classmethod
    async def login_user(cls, data: UserLoginSchema) -> TokenResponseSchema:
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

        return cls._create_tokens(user)

    @classmethod
    async def refresh_tokens(cls, data: RefreshTokenRequestSchema) -> TokenResponseSchema:
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

        return cls._create_tokens(user)

    @classmethod
    async def update_user_name(
        cls,
        user: User,
        data: UserUpdateNameSchema,
    ) -> UserResponseSchema:
        user.name = data.name
        user.updated_at = datetime.now(UTC)

        await user.save()

        return cls.build_user_response(user)

    @classmethod
    async def update_user_settings(
        cls,
        user: User,
        data: UserSettingsUpdateSchema,
    ) -> UserResponseSchema:
        update_data = data.model_dump(exclude_none=True)

        if not update_data:
            return cls.build_user_response(user)

        for field_name, field_value in update_data.items():
            setattr(user, field_name, field_value)

        user.updated_at = datetime.now(UTC)

        await user.save()

        return cls.build_user_response(user)

    @classmethod
    async def update_fcm_token(
        cls,
        user: User,
        data: FCMTokenUpdateSchema,
    ) -> UserResponseSchema:
        user.fcm_token = data.fcm_token
        user.updated_at = datetime.now(UTC)

        await user.save()

        return cls.build_user_response(user)

    @classmethod
    def build_user_response(cls, user: User) -> UserResponseSchema:
        return UserResponseSchema(
            user_id=str(user.id),
            name=user.name,
            email=user.email,
            is_active=user.is_active,
            role=user.role,
            fcm_token=user.fcm_token,
            notification_days_before=user.notification_days_before,
            expiry_notifications_enabled=user.expiry_notifications_enabled,
            theme_mode=user.theme_mode,
            account_type=user.account_type,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
