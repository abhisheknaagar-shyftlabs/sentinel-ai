import uuid

from sqlalchemy import select

from app.models.settings import UserSettings
from app.repositories.base import BaseRepository


class UserSettingsRepository(BaseRepository[UserSettings]):
    model = UserSettings

    async def get_for_user(self, user_id: uuid.UUID) -> UserSettings | None:
        result = await self.session.execute(select(UserSettings).where(UserSettings.user_id == user_id))
        return result.scalar_one_or_none()

    async def get_or_create_for_user(self, user_id: uuid.UUID) -> UserSettings:
        existing = await self.get_for_user(user_id)
        if existing is not None:
            return existing
        return await self.create(UserSettings(user_id=user_id))
