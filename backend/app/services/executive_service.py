import uuid

from pydantic import BaseModel

from app.integrations.docker.schemas import ContainerHealthStatus
from app.integrations.docker.service import DockerMonitoringService
from app.repositories.ai_review_repository import AIReviewRepository
from app.repositories.incident_repository import IncidentRepository
from app.schemas.incident import IncidentStatus

# Weights are a documented first-pass formula, not a validated model. Revisit
# once there's enough real historical data to tune them properly.
_INCIDENT_WEIGHT = 0.40
_CONTAINER_WEIGHT = 0.35
_DEPLOYMENT_CONFIDENCE_WEIGHT = 0.25


class HealthScoreBreakdown(BaseModel):
    incident_resolution_rate: float
    container_health_percent: float
    avg_deployment_confidence: float
    overall_score: int


class ExecutiveMetricsService:
    """Computes a real (if first-pass) engineering health score from actual
    incident, container, and PR review data - no fabricated numbers. Cost
    metrics are deliberately NOT here; those come from the AWS integration
    and gracefully degrade separately when credentials aren't available."""

    def __init__(
        self,
        incidents: IncidentRepository,
        docker_service: DockerMonitoringService,
        reviews: AIReviewRepository,
    ) -> None:
        self.incidents = incidents
        self.docker_service = docker_service
        self.reviews = reviews

    async def compute_engineering_health_score(self, user_id: uuid.UUID) -> HealthScoreBreakdown:
        incident_resolution_rate = await self._incident_resolution_rate()
        container_health_percent = await self._container_health_percent()
        avg_deployment_confidence = await self._avg_deployment_confidence(user_id)

        overall = round(
            incident_resolution_rate * _INCIDENT_WEIGHT
            + container_health_percent * _CONTAINER_WEIGHT
            + avg_deployment_confidence * _DEPLOYMENT_CONFIDENCE_WEIGHT
        )

        return HealthScoreBreakdown(
            incident_resolution_rate=round(incident_resolution_rate, 1),
            container_health_percent=round(container_health_percent, 1),
            avg_deployment_confidence=round(avg_deployment_confidence, 1),
            overall_score=overall,
        )

    async def _incident_resolution_rate(self) -> float:
        incidents = await self.incidents.list_all(limit=500)
        if not incidents:
            return 100.0
        resolved = sum(1 for i in incidents if i.status == IncidentStatus.RESOLVED.value)
        return resolved / len(incidents) * 100

    async def _container_health_percent(self) -> float:
        containers = await self.docker_service.list_containers()
        if not containers:
            return 100.0
        healthy = sum(
            1
            for c in containers
            if c.running and c.health in (ContainerHealthStatus.HEALTHY, ContainerHealthStatus.NONE)
        )
        return healthy / len(containers) * 100

    async def _avg_deployment_confidence(self, user_id: uuid.UUID) -> float:
        reviews = await self.reviews.list_recent_for_user(user_id, limit=50)
        if not reviews:
            return 100.0
        return sum(r.deployment_confidence for r in reviews) / len(reviews)
