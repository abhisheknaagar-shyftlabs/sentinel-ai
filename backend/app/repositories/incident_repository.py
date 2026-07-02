import uuid

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.incident import Incident, IncidentContainer
from app.repositories.base import BaseRepository
from app.schemas.incident import IncidentStatus


class IncidentRepository(BaseRepository[Incident]):
    model = Incident

    _EAGER_OPTIONS = (
        selectinload(Incident.affected_containers),
        selectinload(Incident.events),
    )

    async def get_by_id_with_relations(self, incident_id: uuid.UUID) -> Incident | None:
        result = await self.session.execute(
            select(Incident).options(*self._EAGER_OPTIONS).where(Incident.id == incident_id)
        )
        return result.scalar_one_or_none()

    async def list_all(self, limit: int = 100, offset: int = 0) -> list[Incident]:
        result = await self.session.execute(
            select(Incident)
            .options(*self._EAGER_OPTIONS)
            .order_by(Incident.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def find_active_incident_for_container(self, container_id: str) -> Incident | None:
        """Used by the health monitor (app/services/health_monitor.py) to
        avoid opening a duplicate incident for a container that's already
        being tracked - "active" is anything not yet resolved."""
        result = await self.session.execute(
            select(Incident)
            .join(IncidentContainer)
            .where(
                IncidentContainer.container_id == container_id,
                Incident.status != IncidentStatus.RESOLVED.value,
            )
        )
        return result.scalars().first()
