from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, EmailStr, Field, field_validator
from src.modules.auth.models import AccountType, ThemeMode, UserRole

ALLOWED_NOTIFICATION_DAYS = {0, 1, 3, 5, 7}


class UserRegisterSchema(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        if not any(char.isupper() for char in value):
            raise ValueError('Password must contain at least one uppercase letter')

        if not any(char.islower() for char in value):
            raise ValueError('Password must contain at least one lowercase letter')

        if not any(char.isdigit() for char in value):
            raise ValueError('Password must contain at least one number')

        if not any(not char.isalnum() for char in value):
            raise ValueError('Password must contain at least one special character')

        return value


class UserLoginSchema(BaseModel):
    email: EmailStr
    password: str


class UserUpdateNameSchema(BaseModel):
    name: str = Field(min_length=2, max_length=100)


class UserSettingsUpdateSchema(BaseModel):
    notification_days_before: Annotated[
        list[int] | None,
        Field(default=None, min_length=1),
    ] = None
    expiry_notifications_enabled: bool | None = None
    theme_mode: ThemeMode | None = None

    @field_validator('notification_days_before')
    @classmethod
    def validate_notification_days_before(cls, value: list[int] | None) -> list[int] | None:
        if value is None:
            return value

        unique_days = sorted(set(value), reverse=True)

        for day in unique_days:
            if day not in ALLOWED_NOTIFICATION_DAYS:
                raise ValueError(
                    'Notification days must be one of: 0, 1, 3, 5, 7',
                )

        return unique_days


class FCMTokenUpdateSchema(BaseModel):
    fcm_token: str | None = Field(default=None, max_length=500)


class UserResponseSchema(BaseModel):
    user_id: str
    name: str
    email: EmailStr
    is_active: bool
    role: UserRole
    fcm_token: str | None = None
    notification_days_before: list[int]
    expiry_notifications_enabled: bool
    theme_mode: ThemeMode
    account_type: AccountType
    created_at: datetime
    updated_at: datetime


class TokenResponseSchema(BaseModel):
    access_token: str
    refresh_token: str


class RefreshTokenRequestSchema(BaseModel):
    refresh_token: str
