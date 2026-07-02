import uuid
from typing import Any

from app.models.settings import UserSettings
from app.repositories.settings_repository import UserSettingsRepository


class SettingsService:
    def __init__(self, repository: UserSettingsRepository) -> None:
        self.repository = repository

    async def get_settings(self, user_id: uuid.UUID) -> UserSettings:
        return await self.repository.get_or_create_for_user(user_id)

    async def update_section(self, user_id: uuid.UUID, values: dict[str, Any]) -> UserSettings:
        """`values` must already be validated/narrowed to the fields for one
        section - that validation happens at the request schema layer
        (app/api/frontend/settings.py), not here."""
        settings = await self.repository.get_or_create_for_user(user_id)
        for key, value in values.items():
            setattr(settings, key, value)
        await self.repository.session.flush()
        return settings
