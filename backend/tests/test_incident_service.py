import types

import pytest

from app.agents.production.schemas import IncidentDiagnosis, Severity
from app.core.exceptions import ConflictError, NotFoundError
from app.integrations.docker.exceptions import DockerContainerNotFoundError
from app.integrations.slack.client import SlackClient
from app.repositories.incident_repository import IncidentRepository
from app.schemas.incident import IncidentCreateRequest, IncidentStatus
from app.services.incident_service import IncidentService


def _fake_container(container_id="abc123", name="postgres", image="postgres:16-alpine"):
    return types.SimpleNamespace(id=container_id, name=name, image=image)


class FakeDockerService:
    def __init__(self, container=None, fail_restart=False):
        self.container = container
        self.fail_restart = fail_restart
        self.restart_calls = []

    async def get_container(self, container_id):
        if self.container is None:
            raise DockerContainerNotFoundError(container_id)
        return self.container

    async def restart_container(self, container_id, timeout=10):
        self.restart_calls.append(container_id)
        if self.fail_restart:
            raise RuntimeError("restart failed")


def _rca_response(auto_restart_safe: bool) -> IncidentDiagnosis:
    return IncidentDiagnosis(
        summary="Out of memory.",
        severity=Severity.HIGH,
        confidence=80,
        recommended_actions=["Increase memory limit"],
        auto_restart_safe=auto_restart_safe,
        auto_restart_rationale="Safe to restart." if auto_restart_safe else "Needs a human look first.",
        requires_human_intervention=not auto_restart_safe,
    )


class FakeRootCauseService:
    def __init__(self, response=None, fail=False):
        self.response = response
        self.fail = fail
        self.calls = []

    async def diagnose_incident(self, container_id):
        self.calls.append(container_id)
        if self.fail:
            raise RuntimeError("analysis failed")
        return self.response


@pytest.fixture
def incident_repo(db_session):
    return IncidentRepository(db_session)


async def test_create_incident_collects_docker_metadata_and_logs_event(incident_repo):
    docker_service = FakeDockerService(container=_fake_container())
    service = IncidentService(incident_repo, docker_service, FakeRootCauseService(), SlackClient(None))

    incident = await service.create_incident(
        IncidentCreateRequest(title="Postgres down", container_ids=["postgres"])
    )

    assert incident.status == IncidentStatus.OPEN.value
    assert len(incident.affected_containers) == 1
    assert incident.affected_containers[0].container_name == "postgres"
    assert len(incident.events) == 1
    assert incident.events[0].event_type == "incident_created"


async def test_create_incident_missing_container_raises(incident_repo):
    docker_service = FakeDockerService(container=None)
    service = IncidentService(incident_repo, docker_service, FakeRootCauseService(), SlackClient(None))

    with pytest.raises(DockerContainerNotFoundError):
        await service.create_incident(IncidentCreateRequest(title="X", container_ids=["missing"]))


async def test_analyze_incident_moves_to_recovery_available_when_safe(incident_repo):
    docker_service = FakeDockerService(container=_fake_container())
    root_cause_service = FakeRootCauseService(response=_rca_response(auto_restart_safe=True))
    service = IncidentService(incident_repo, docker_service, root_cause_service, SlackClient(None))

    incident = await service.create_incident(
        IncidentCreateRequest(title="Postgres down", container_ids=["postgres"])
    )
    analyzed = await service.analyze_incident(incident.id)

    assert analyzed.status == IncidentStatus.RECOVERY_AVAILABLE.value
    assert analyzed.root_cause_summary == "Out of memory."
    assert analyzed.root_cause_confidence == 80
    event_types = [e.event_type for e in analyzed.events]
    assert "analysis_started" in event_types
    assert "analysis_completed" in event_types


async def test_analyze_incident_stays_analyzed_when_not_safe_to_restart(incident_repo):
    docker_service = FakeDockerService(container=_fake_container())
    root_cause_service = FakeRootCauseService(response=_rca_response(auto_restart_safe=False))
    service = IncidentService(incident_repo, docker_service, root_cause_service, SlackClient(None))

    incident = await service.create_incident(
        IncidentCreateRequest(title="Postgres down", container_ids=["postgres"])
    )
    analyzed = await service.analyze_incident(incident.id)

    assert analyzed.status == IncidentStatus.ANALYZED.value


async def test_analyze_incident_without_containers_raises(incident_repo):
    service = IncidentService(incident_repo, FakeDockerService(), FakeRootCauseService(), SlackClient(None))
    incident = await service.create_incident(IncidentCreateRequest(title="No containers"))

    with pytest.raises(ConflictError):
        await service.analyze_incident(incident.id)


async def test_analyze_incident_failure_reverts_status_and_logs_event(incident_repo):
    docker_service = FakeDockerService(container=_fake_container())
    root_cause_service = FakeRootCauseService(fail=True)
    service = IncidentService(incident_repo, docker_service, root_cause_service, SlackClient(None))

    incident = await service.create_incident(
        IncidentCreateRequest(title="Postgres down", container_ids=["postgres"])
    )
    with pytest.raises(RuntimeError):
        await service.analyze_incident(incident.id)

    refreshed = await service.get_incident(incident.id)
    assert refreshed.status == IncidentStatus.OPEN.value
    assert "analysis_failed" in [e.event_type for e in refreshed.events]


async def test_recover_incident_requires_recovery_available_status(incident_repo):
    docker_service = FakeDockerService(container=_fake_container())
    service = IncidentService(incident_repo, docker_service, FakeRootCauseService(), SlackClient(None))

    incident = await service.create_incident(
        IncidentCreateRequest(title="Postgres down", container_ids=["postgres"])
    )
    with pytest.raises(ConflictError):
        await service.recover_incident(incident.id)


async def test_recover_incident_restarts_and_resolves(incident_repo):
    docker_service = FakeDockerService(container=_fake_container())
    root_cause_service = FakeRootCauseService(response=_rca_response(auto_restart_safe=True))
    service = IncidentService(incident_repo, docker_service, root_cause_service, SlackClient(None))

    incident = await service.create_incident(
        IncidentCreateRequest(title="Postgres down", container_ids=["postgres"])
    )
    await service.analyze_incident(incident.id)
    resolved = await service.recover_incident(incident.id)

    assert resolved.status == IncidentStatus.RESOLVED.value
    assert resolved.recovery_executed is True
    assert resolved.resolved_at is not None
    assert docker_service.restart_calls == ["abc123"]
    event_types = [e.event_type for e in resolved.events]
    assert "recovery_started" in event_types
    assert "recovery_completed" in event_types
    assert "resolved" in event_types


async def test_recover_incident_failure_keeps_recovery_available_and_logs_event(incident_repo):
    docker_service = FakeDockerService(container=_fake_container(), fail_restart=True)
    root_cause_service = FakeRootCauseService(response=_rca_response(auto_restart_safe=True))
    service = IncidentService(incident_repo, docker_service, root_cause_service, SlackClient(None))

    incident = await service.create_incident(
        IncidentCreateRequest(title="Postgres down", container_ids=["postgres"])
    )
    await service.analyze_incident(incident.id)

    with pytest.raises(RuntimeError):
        await service.recover_incident(incident.id)

    refreshed = await service.get_incident(incident.id)
    assert refreshed.status == IncidentStatus.RECOVERY_AVAILABLE.value
    assert refreshed.recovery_executed is False
    assert "recovery_failed" in [e.event_type for e in refreshed.events]


async def test_get_unknown_incident_raises_not_found(incident_repo):
    import uuid

    service = IncidentService(incident_repo, FakeDockerService(), FakeRootCauseService(), SlackClient(None))
    with pytest.raises(NotFoundError):
        await service.get_incident(uuid.uuid4())


async def test_list_incidents_orders_most_recent_first(incident_repo):
    docker_service = FakeDockerService(container=_fake_container())
    service = IncidentService(incident_repo, docker_service, FakeRootCauseService(), SlackClient(None))

    first = await service.create_incident(IncidentCreateRequest(title="First"))
    second = await service.create_incident(IncidentCreateRequest(title="Second"))

    incidents = await service.list_incidents()
    assert [i.id for i in incidents[:2]] == [second.id, first.id]
