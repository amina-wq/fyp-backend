import logging
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
from src.modules.auth.token_blacklist import blacklist_token, is_token_blacklisted
from src.modules.inventory.models import InventoryItem, InventoryStatus
from src.modules.notifications.scheduling import build_scheduled_notifications

logger = logging.getLogger(__name__)


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

        logger.info(
            'User registered: user_id=%s',
            user.id,
        )

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

        logger.info(
            'User logged in: user_id=%s',
            user.id,
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

        if await is_token_blacklisted(payload):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Refresh token has been revoked',
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

        await blacklist_token(payload)

        logger.info(
            'Token refreshed: user_id=%s',
            user.id,
        )

        return cls._create_tokens(user)

    @classmethod
    async def logout_user(
        cls,
        access_token: str,
        data: LogoutRequestSchema,
    ) -> LogoutResponseSchema:
        try:
            access_payload = validate_jwt(access_token, expected_type='access')
            refresh_payload = validate_jwt(data.refresh_token, expected_type='refresh')
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Invalid or expired token',
            )

        if access_payload['sub'] != refresh_payload['sub']:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Token subject mismatch',
            )

        await blacklist_token(access_payload)
        await blacklist_token(refresh_payload)

        logger.info(
            'User logged out: user_id=%s',
            access_payload['sub'],
        )

        return LogoutResponseSchema(detail='Logged out successfully')

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
    async def _reschedule_inventory_notifications_for_user(
        cls,
        user: User,
    ) -> None:
        items = await InventoryItem.find(
            InventoryItem.user_id == user.id,
            InventoryItem.status == InventoryStatus.ACTIVE,
        ).to_list()

        for item in items:
            if user.expiry_notifications_enabled:
                item.scheduled_notifications = build_scheduled_notifications(
                    expiration_date=item.expiration_date,
                    notification_days_before=user.notification_days_before,
                )
            else:
                item.scheduled_notifications = []

            item.updated_at = datetime.now(UTC)

            await item.save()

        logger.info(
            'Inventory notifications rescheduled: '
            'user_id=%s item_count=%s notifications_enabled=%s notification_days=%s',
            user.id,
            len(items),
            user.expiry_notifications_enabled,
            user.notification_days_before,
        )

    @classmethod
    async def update_user_settings(
        cls,
        user: User,
        data: UserSettingsUpdateSchema,
    ) -> UserResponseSchema:
        update_data = data.model_dump(exclude_none=True)

        if not update_data:
            return cls.build_user_response(user)

        should_reschedule_notifications = (
            'notification_days_before' in update_data or 'expiry_notifications_enabled' in update_data
        )

        for field_name, field_value in update_data.items():
            setattr(user, field_name, field_value)

        user.updated_at = datetime.now(UTC)

        await user.save()

        logger.info(
            'User settings updated: user_id=%s fields=%s',
            user.id,
            sorted(update_data.keys()),
        )

        if should_reschedule_notifications:
            await cls._reschedule_inventory_notifications_for_user(user)

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
