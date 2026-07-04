from datetime import datetime

from pydantic import BaseModel, EmailStr, Field
from src.modules.auth.models import AccountType, UserRole


class UserRegisterSchema(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserLoginSchema(BaseModel):
    email: EmailStr
    password: str


class UserResponseSchema(BaseModel):
    user_id: str
    name: str
    email: EmailStr
    is_active: bool
    role: UserRole
    fcm_token: str | None = None
    notification_days_before: list[int]
    account_type: AccountType
    created_at: datetime
    updated_at: datetime


class TokenResponseSchema(BaseModel):
    access_token: str
    refresh_token: str


class RefreshTokenRequestSchema(BaseModel):
    refresh_token: str
