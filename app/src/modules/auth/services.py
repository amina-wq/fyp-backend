import logging

from fastapi import HTTPException, status
from src.core.security import create_access_token, hash_password, verify_password
from src.modules.auth.models import User
from src.modules.auth.schemas import (
    TokenResponseSchema,
    UserLoginSchema,
    UserRegisterSchema,
)

logger = logging.getLogger(__name__)


class AuthService:
    def _create_tokens(self, user: User) -> TokenResponseSchema:
        access_token = create_access_token(subject=str(user.id))

        return TokenResponseSchema(
            access_token=access_token,
        )

    async def register_user(self, data: UserRegisterSchema) -> TokenResponseSchema:
        logger.info('Registration attempt for email: %s', data.email)

        existing_user = await User.find_one(User.email == data.email)

        if existing_user:
            logger.warning('Registration failed: email already registered: %s', data.email)
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

        logger.info('User registered successfully: %s', user.email)

        return self._create_tokens(user)

    async def login_user(self, data: UserLoginSchema) -> TokenResponseSchema:
        logger.info('Login attempt for email: %s', data.email)

        user = await User.find_one(User.email == data.email)

        if not user:
            logger.warning('Login failed: user not found for email: %s', data.email)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Incorrect email or password',
            )

        if not verify_password(data.password, user.hashed_password):
            logger.warning('Login failed: incorrect password for email: %s', data.email)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Incorrect email or password',
            )

        if not user.is_active:
            logger.warning('Login failed: inactive account for email: %s', data.email)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='User account is inactive',
            )

        logger.info('User logged in successfully: %s', user.email)

        return self._create_tokens(user)
