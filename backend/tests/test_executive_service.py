import types
import uuid

from app.integrations.docker.schemas import ContainerHealthStatus
from app.services.executive_service import ExecutiveMetricsService


def _container(running=True, health=ContainerHealthStatus.HEALTHY):
    return types.SimpleNamespace(running=running, health=health)


class FakeIncidentRepository:
    def __init__(self, incidents):
        self._incidents = incidents

    async def list_all(self, limit=500):
        return self._incidents


class FakeDockerService:
    def __init__(self, containers):
        self._containers = containers

    async def list_containers(self):
        return self._containers


class FakeReviewRepository:
    def __init__(self, reviews):
        self._reviews = reviews

    async def list_recent_for_user(self, user_id, limit=50):
        return self._reviews


def _incident(status):
    return types.SimpleNamespace(status=status)


def _review(deployment_confidence):
    return types.SimpleNamespace(deployment_confidence=deployment_confidence)


async def test_health_score_defaults_to_100_with_no_data():
    service = ExecutiveMetricsService(
        FakeIncidentRepository([]), FakeDockerService([]), FakeReviewRepository([])
    )
    score = await service.compute_engineering_health_score(uuid.uuid4())
    assert score.overall_score == 100


async def test_health_score_reflects_real_mixed_data():
    incidents = [_incident("resolved"), _incident("resolved"), _incident("open")]
    containers = [_container(True, ContainerHealthStatus.HEALTHY), _container(False, ContainerHealthStatus.UNHEALTHY)]
    reviews = [_review(90), _review(70)]

    service = ExecutiveMetricsService(
        FakeIncidentRepository(incidents), FakeDockerService(containers), FakeReviewRepository(reviews)
    )
    score = await service.compute_engineering_health_score(uuid.uuid4())

    assert score.incident_resolution_rate == round(2 / 3 * 100, 1)
    assert score.container_health_percent == 50.0
    assert score.avg_deployment_confidence == 80.0
    # 66.7*0.4 + 50*0.35 + 80*0.25 = 26.68 + 17.5 + 20 = 64.18 -> 64
    assert score.overall_score == 64
