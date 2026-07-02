import uuid

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import UnauthorizedError
from app.database.deps import get_db
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.security.jwt import TokenType, decode_token

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None:
        raise UnauthorizedError("Missing authentication credentials")

    try:
        payload = decode_token(credentials.credentials)
    except jwt.ExpiredSignatureError:
        raise UnauthorizedError("Token has expired") from None
    except jwt.InvalidTokenError:
        raise UnauthorizedError("Invalid authentication token") from None

    if payload.get("type") != TokenType.ACCESS.value:
        raise UnauthorizedError("Invalid token type")

    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedError("Invalid token payload")

    user = await UserRepository(db).get_by_id(uuid.UUID(user_id))
    if user is None or not user.is_active:
        raise UnauthorizedError("User not found or inactive")

    return user
