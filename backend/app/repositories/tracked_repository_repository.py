import uuid

from sqlalchemy import select

from app.models.integration import Integration
from app.models.repository import TrackedRepository
from app.repositories.base import BaseRepository


class TrackedRepositoryRepository(BaseRepository[TrackedRepository]):
    model = TrackedRepository

    async def get_by_github_id(self, integration_id: uuid.UUID, github_id: int) -> TrackedRepository | None:
        result = await self.session.execute(
            select(TrackedRepository).where(
                TrackedRepository.integration_id == integration_id,
                TrackedRepository.github_id == github_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_user(self, user_id: uuid.UUID) -> list[TrackedRepository]:
        result = await self.session.execute(
            select(TrackedRepository)
            .join(Integration, TrackedRepository.integration_id == Integration.id)
            .where(Integration.user_id == user_id)
            .order_by(TrackedRepository.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_for_user(self, repository_id: uuid.UUID, user_id: uuid.UUID) -> TrackedRepository | None:
        result = await self.session.execute(
            select(TrackedRepository)
            .join(Integration, TrackedRepository.integration_id == Integration.id)
            .where(TrackedRepository.id == repository_id, Integration.user_id == user_id)
        )
        return result.scalar_one_or_none()
