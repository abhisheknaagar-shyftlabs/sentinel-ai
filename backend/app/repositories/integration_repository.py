import uuid

from sqlalchemy import select

from app.models.integration import Integration
from app.repositories.base import BaseRepository


class IntegrationRepository(BaseRepository[Integration]):
    model = Integration

    async def list_for_user(self, user_id: uuid.UUID) -> list[Integration]:
        result = await self.session.execute(
            select(Integration).where(Integration.user_id == user_id).order_by(Integration.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_for_user(self, integration_id: uuid.UUID, user_id: uuid.UUID) -> Integration | None:
        result = await self.session.execute(
            select(Integration).where(Integration.id == integration_id, Integration.user_id == user_id)
        )
        return result.scalar_one_or_none()
