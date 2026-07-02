import uuid

import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, UnauthorizedError
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import TokenPair
from app.schemas.user import UserCreate
from app.security.jwt import TokenType, create_access_token, create_refresh_token, decode_token
from app.security.password import hash_password, verify_password


class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.users = UserRepository(session)

    async def register(self, payload: UserCreate) -> User:
        existing = await self.users.get_by_email(payload.email)
        if existing is not None:
            raise ConflictError("A user with this email already exists")

        user = User(
            email=payload.email,
            full_name=payload.full_name,
            hashed_password=hash_password(payload.password),
        )
        return await self.users.create(user)

    async def authenticate(self, email: str, password: str) -> User:
        user = await self.users.get_by_email(email)
        if user is None or not verify_password(password, user.hashed_password):
            raise UnauthorizedError("Invalid email or password")
        if not user.is_active:
            raise UnauthorizedError("User account is inactive")
        return user

    def issue_tokens(self, user: User) -> TokenPair:
        subject = str(user.id)
        return TokenPair(
            access_token=create_access_token(subject),
            refresh_token=create_refresh_token(subject),
        )

    async def refresh(self, refresh_token: str) -> TokenPair:
        try:
            payload = decode_token(refresh_token)
        except jwt.ExpiredSignatureError:
            raise UnauthorizedError("Refresh token has expired") from None
        except jwt.InvalidTokenError:
            raise UnauthorizedError("Invalid refresh token") from None

        if payload.get("type") != TokenType.REFRESH.value:
            raise UnauthorizedError("Invalid token type")

        user_id = payload.get("sub")
        user = await self.users.get_by_id(uuid.UUID(user_id)) if user_id else None
        if user is None or not user.is_active:
            raise UnauthorizedError("User not found or inactive")

        return self.issue_tokens(user)
