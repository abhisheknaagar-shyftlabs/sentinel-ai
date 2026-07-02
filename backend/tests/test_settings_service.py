import uuid

from app.repositories.settings_repository import UserSettingsRepository
from app.services.settings_service import SettingsService


async def test_get_settings_creates_defaults_on_first_access(db_session):
    service = SettingsService(UserSettingsRepository(db_session))
    user_id = uuid.uuid4()

    settings = await service.get_settings(user_id)

    assert settings.workspace_name == "My Workspace"
    assert settings.risk_sensitivity == "balanced"
    assert settings.min_confidence_threshold == 80


async def test_get_settings_is_idempotent(db_session):
    service = SettingsService(UserSettingsRepository(db_session))
    user_id = uuid.uuid4()

    first = await service.get_settings(user_id)
    second = await service.get_settings(user_id)

    assert first.id == second.id


async def test_update_section_persists_changes(db_session):
    service = SettingsService(UserSettingsRepository(db_session))
    user_id = uuid.uuid4()

    await service.get_settings(user_id)
    updated = await service.update_section(
        user_id, {"workspace_name": "Acme Engineering", "timezone": "America/New_York"}
    )

    assert updated.workspace_name == "Acme Engineering"
    assert updated.timezone == "America/New_York"

    refetched = await service.get_settings(user_id)
    assert refetched.workspace_name == "Acme Engineering"
