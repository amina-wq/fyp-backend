from datetime import UTC, datetime
from enum import Enum
from typing import Annotated

from beanie import Document, Indexed
from pydantic import EmailStr, Field


class AccountType(str, Enum):
    PERSONAL = 'personal'
    BUSINESS = 'business'
    FAMILY = 'family'


class User(Document):
    name: str
    email: Annotated[EmailStr, Indexed(unique=True)]
    hashed_password: str
    is_active: bool = True
    fcm_token: str | None = None
    notification_days_before: list[int] = Field(default_factory=lambda: [3, 1])
    account_type: AccountType = AccountType.PERSONAL
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = 'users'
