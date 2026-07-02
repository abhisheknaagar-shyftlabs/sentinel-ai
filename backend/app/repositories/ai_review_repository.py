import uuid

from sqlalchemy import select

from app.models.integration import Integration
from app.models.repository import TrackedRepository
from app.models.review import AIReview
from app.repositories.base import BaseRepository


class AIReviewRepository(BaseRepository[AIReview]):
    model = AIReview

    async def list_for_repository(self, repository_id: uuid.UUID) -> list[AIReview]:
        result = await self.session.execute(
            select(AIReview)
            .where(AIReview.repository_id == repository_id)
            .order_by(AIReview.review_timestamp.desc())
        )
        return list(result.scalars().all())

    async def list_recent_for_user(self, user_id: uuid.UUID, limit: int = 100) -> list[AIReview]:
        result = await self.session.execute(
            select(AIReview)
            .join(TrackedRepository, AIReview.repository_id == TrackedRepository.id)
            .join(Integration, TrackedRepository.integration_id == Integration.id)
            .where(Integration.user_id == user_id)
            .order_by(AIReview.review_timestamp.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
