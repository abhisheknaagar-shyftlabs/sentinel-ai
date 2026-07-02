import uuid

from sqlalchemy import select

from app.models.ai_fix import AIFix
from app.models.integration import Integration
from app.models.repository import TrackedRepository
from app.repositories.base import BaseRepository


class AIFixRepository(BaseRepository[AIFix]):
    model = AIFix

    async def bulk_create(self, fixes: list[AIFix]) -> None:
        self.session.add_all(fixes)
        await self.session.flush()

    async def list_for_repository(self, repository_id: uuid.UUID, limit: int = 50) -> list[AIFix]:
        result = await self.session.execute(
            select(AIFix)
            .where(AIFix.repository_id == repository_id)
            .order_by(AIFix.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_recent_for_user(self, user_id: uuid.UUID, limit: int = 50) -> list[AIFix]:
        result = await self.session.execute(
            select(AIFix)
            .join(TrackedRepository, AIFix.repository_id == TrackedRepository.id)
            .join(Integration, TrackedRepository.integration_id == Integration.id)
            .where(Integration.user_id == user_id)
            .order_by(AIFix.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
