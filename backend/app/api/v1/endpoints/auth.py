from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import success_envelope
from app.database.deps import get_db
from app.models.user import User
from app.schemas.auth import AuthResponse, LoginRequest, RefreshRequest, TokenPair
from app.schemas.user import UserCreate, UserRead
from app.security.dependencies import get_current_user
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    user = await service.register(payload)
    tokens = service.issue_tokens(user)
    response = AuthResponse(user=UserRead.model_validate(user), **tokens.model_dump())
    return success_envelope(response.model_dump(mode="json"), "User registered successfully")


@router.post("/login")
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    user = await service.authenticate(payload.email, payload.password)
    tokens = service.issue_tokens(user)
    response = AuthResponse(user=UserRead.model_validate(user), **tokens.model_dump())
    return success_envelope(response.model_dump(mode="json"), "Login successful")


@router.post("/refresh")
async def refresh(payload: RefreshRequest, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    tokens: TokenPair = await service.refresh(payload.refresh_token)
    return success_envelope(tokens.model_dump(), "Token refreshed")


@router.get("/me")
async def me(current_user: User = Depends(get_current_user)):
    return success_envelope(UserRead.model_validate(current_user).model_dump(mode="json"))
