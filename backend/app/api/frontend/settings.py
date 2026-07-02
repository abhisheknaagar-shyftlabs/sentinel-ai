from typing import Any

from fastapi import APIRouter, Body, Depends
from pydantic import EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.database.deps import get_db
from app.models.settings import UserSettings
from app.models.user import User
from app.repositories.settings_repository import UserSettingsRepository
from app.schemas.camel import CamelModel
from app.security.dependencies import get_current_user
from app.services.settings_service import SettingsService

router = APIRouter(prefix="/settings", tags=["frontend-settings"])


class WorkspaceSection(CamelModel):
    workspace_name: str = Field(min_length=2)
    timezone: str
    default_branch: str


class NotificationsSection(CamelModel):
    incident_alerts: bool
    pr_risk_alerts: bool
    weekly_digest: bool
    cost_alerts: bool
    notification_email: EmailStr | None = None


class AIPreferencesSection(CamelModel):
    auto_fix_enabled: bool
    auto_recovery_enabled: bool
    risk_sensitivity: str = Field(pattern="^(conservative|balanced|aggressive)$")
    min_confidence_threshold: int = Field(ge=0, le=100)


class SettingsResponse(CamelModel):
    workspace: WorkspaceSection
    notifications: NotificationsSection
    ai_preferences: AIPreferencesSection


_SECTION_MODELS: dict[str, type[CamelModel]] = {
    "workspace": WorkspaceSection,
    "notifications": NotificationsSection,
    "aiPreferences": AIPreferencesSection,
}


def _to_response(settings: UserSettings) -> SettingsResponse:
    return SettingsResponse(
        workspace=WorkspaceSection(
            workspace_name=settings.workspace_name,
            timezone=settings.timezone,
            default_branch=settings.default_branch,
        ),
        notifications=NotificationsSection(
            incident_alerts=settings.incident_alerts,
            pr_risk_alerts=settings.pr_risk_alerts,
            weekly_digest=settings.weekly_digest,
            cost_alerts=settings.cost_alerts,
            notification_email=settings.notification_email,
        ),
        ai_preferences=AIPreferencesSection(
            auto_fix_enabled=settings.auto_fix_enabled,
            auto_recovery_enabled=settings.auto_recovery_enabled,
            risk_sensitivity=settings.risk_sensitivity,
            min_confidence_threshold=settings.min_confidence_threshold,
        ),
    )


def get_settings_service(db: AsyncSession = Depends(get_db)) -> SettingsService:
    return SettingsService(UserSettingsRepository(db))


@router.get("", response_model=SettingsResponse)
async def get_settings_endpoint(
    current_user: User = Depends(get_current_user),
    service: SettingsService = Depends(get_settings_service),
):
    settings = await service.get_settings(current_user.id)
    return _to_response(settings)


@router.patch("/{section}", response_model=SettingsResponse)
async def update_settings_section(
    section: str,
    payload: dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_user),
    service: SettingsService = Depends(get_settings_service),
):
    model = _SECTION_MODELS.get(section)
    if model is None:
        raise NotFoundError(f"Unknown settings section '{section}'")

    validated = model.model_validate(payload)
    settings = await service.update_section(current_user.id, validated.model_dump())
    return _to_response(settings)
