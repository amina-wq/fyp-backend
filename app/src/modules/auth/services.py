from fastapi import HTTPException, status
from src.core.security import verify_password, hash_password, create_access_token
from src.modules.auth.models import User
from src.modules.auth.schemas import (
    UserRegisterSchema,
    UserLoginSchema,
    TokenResponseSchema,
)

class AuthService:
    async def register_user(self, data:UserRegisterSchema) -> TokenResponseSchema:
        existing_user = await User.find_one(User.email == data.email)

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Email already registered'
            )

        user = User(
            name=data.name,
            email=data.email,
            hashed_password=hash_password(data.password),
        )

        await user.insert()

        access_token = create_access_token(subject=str(user.id))

        return TokenResponseSchema(
            access_token=access_token,
        )


    async def login_user(self, data:UserLoginSchema) -> TokenResponseSchema:
        user = await User.find_one(User.email == data.email)

        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Incorrect email or password')

        if not verify_password(data.password, user.hashed_password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Incorrect email or password')

        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='User account is inactive')

        access_token = create_access_token(subject=str(user.id))

        return TokenResponseSchema(
            access_token=access_token,
        )