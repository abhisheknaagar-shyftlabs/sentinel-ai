from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.deps import get_db
from app.repositories.settings_repository import UserSettingsRepository
from app.schemas.camel import CamelModel
from app.services.auth_service import AuthService
from app.services.settings_service import SettingsService

router = APIRouter(prefix="/auth", tags=["frontend-auth"])


class FrontendLoginRequest(BaseModel):
    email: str
    password: str


class FrontendAuthUser(CamelModel):
    name: str
    email: str
    workspace: str


class FrontendLoginResponse(CamelModel):
    token: str
    user: FrontendAuthUser


@router.post("/login", response_model=FrontendLoginResponse)
async def login(payload: FrontendLoginRequest, db: AsyncSession = Depends(get_db)):
    """Reshapes the real /api/v1/auth/login flow to match frontend/API_CONTRACT.md
    exactly - same AuthService, same credential check, same 401 on failure
    (AuthService.authenticate already raises UnauthorizedError -> 401 via the
    app-wide exception handler). Only the response shape differs."""
    auth_service = AuthService(db)
    user = await auth_service.authenticate(payload.email, payload.password)
    tokens = auth_service.issue_tokens(user)

    settings_service = SettingsService(UserSettingsRepository(db))
    user_settings = await settings_service.get_settings(user.id)

    return FrontendLoginResponse(
        token=tokens.access_token,
        user=FrontendAuthUser(
            name=user.full_name or user.email.split("@")[0],
            email=user.email,
            workspace=user_settings.workspace_name,
        ),
    )
