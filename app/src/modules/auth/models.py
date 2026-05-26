from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Annotated
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
    is_active: bool=True
    fcm_token: Optional[str] = None
    notification_days_before: list[int] = Field(default_factory=lambda: [3, 1])
    account_type: AccountType = AccountType.PERSONAL
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = 'users'
