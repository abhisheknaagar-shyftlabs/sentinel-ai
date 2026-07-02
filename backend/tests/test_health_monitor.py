from app.agents.production.schemas import IncidentDiagnosis, Severity
from app.continuum.client import ContinuumClient
from app.integrations.docker.client import DockerClient
from app.integrations.docker.schemas import ContainerHealthStatus, ContainerSummary
from app.integrations.docker.service import DockerMonitoringService
from app.integrations.slack.client import SlackClient
from app.repositories.incident_repository import IncidentRepository
from app.schemas.incident import IncidentStatus
from app.services.health_monitor import HealthMonitor, _is_collapsed
from app.utils.time import utc_now
from tests.test_root_cause import FakeContainer

SAMPLE_DIAGNOSIS = IncidentDiagnosis(
    summary="Out of memory during startup.",
    severity=Severity.HIGH,
    confidence=70,
    recommended_actions=["Increase memory limit"],
    auto_restart_safe=False,
    auto_restart_rationale="Would likely repeat the failure.",
    requires_human_intervention=True,
)

RUNNING_HEALTHY = ContainerSummary(
    id="web1",
    short_id="web1",
    name="web",
    image="sentinel/web:latest",
    status="running",
    health=ContainerHealthStatus.HEALTHY,
    running=True,
    created_at=utc_now(),
    started_at=utc_now(),
    restart_count=0,
    exposed_ports=[],
)


def _summary(**overrides) -> ContainerSummary:
    base = RUNNING_HEALTHY.model_dump()
    base.update(overrides)
    return ContainerSummary(**base)


class _HealthyContainer:
    """Raw-docker-object-shaped fake (mirrors FakeContainer in
    tests.test_root_cause) for exercising DockerMonitoringService.list_containers,
    which converts from the raw SDK object's .attrs, not a ContainerSummary."""

    id = "web1"
    short_id = "web1"
    name = "web"
    status = "running"
    attrs = {
        "State": {"Status": "running", "Running": True},
        "Created": "2026-07-01T09:59:00.000000000Z",
        "RestartCount": 0,
        "Config": {"Image": "sentinel/web:latest", "Cmd": ["web"]},
        "NetworkSettings": {"Ports": {}},
        "Mounts": [],
    }


def test_is_collapsed_true_for_exited_container():
    assert _is_collapsed(_summary(status="exited", running=False)) is True


def test_is_collapsed_true_for_unhealthy_container():
    assert _is_collapsed(_summary(health=ContainerHealthStatus.UNHEALTHY)) is True


def test_is_collapsed_false_for_running_healthy_container():
    assert _is_collapsed(RUNNING_HEALTHY) is False


def test_is_collapsed_false_for_container_still_starting():
    assert _is_collapsed(_summary(status="created", running=False)) is False


def _patch_docker(monkeypatch, container: FakeContainer):
    async def fake_list_containers(self, all=True):
        return [container]

    async def fake_get_container(self, container_id):
        return container

    async def fake_container_stats(self, container_id):
        return container.stats(stream=False)

    async def fake_container_logs(self, container_id, tail, timestamps):
        return container.logs(tail, timestamps)

    monkeypatch.setattr(DockerClient, "list_containers", fake_list_containers)
    monkeypatch.setattr(DockerClient, "get_container", fake_get_container)
    monkeypatch.setattr(DockerClient, "container_stats", fake_container_stats)
    monkeypatch.setattr(DockerClient, "container_logs", fake_container_logs)


def _patch_continuum(monkeypatch, response=SAMPLE_DIAGNOSIS):
    async def fake_run_prompt(self, **kwargs):
        return response

    monkeypatch.setattr(ContinuumClient, "run_prompt", fake_run_prompt)


async def test_poll_once_opens_and_analyzes_incident_for_collapsed_container(db_session, monkeypatch):
    _patch_docker(monkeypatch, FakeContainer())
    _patch_continuum(monkeypatch, response=SAMPLE_DIAGNOSIS)
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/test")
    from app.config.settings import get_settings

    get_settings.cache_clear()

    posted = []

    async def fake_post_message(self, text, blocks=None):
        posted.append((text, blocks))

    monkeypatch.setattr(SlackClient, "post_message", fake_post_message)

    docker_service = DockerMonitoringService(DockerClient())
    monitor = HealthMonitor()
    await monitor._poll_once(docker_service)

    incidents = IncidentRepository(db_session)
    all_incidents = await incidents.list_all()
    assert len(all_incidents) == 1
    incident = all_incidents[0]
    assert incident.status == IncidentStatus.ANALYZED.value  # SAMPLE_DIAGNOSIS is not auto-restart-safe
    assert incident.affected_containers[0].container_id == "abc123def456"
    assert len(posted) == 1


async def test_poll_once_does_not_duplicate_incident_for_already_tracked_container(db_session, monkeypatch):
    _patch_docker(monkeypatch, FakeContainer())
    _patch_continuum(monkeypatch, response=SAMPLE_DIAGNOSIS)

    async def fake_post_message(self, text, blocks=None):
        return None

    monkeypatch.setattr(SlackClient, "post_message", fake_post_message)

    docker_service = DockerMonitoringService(DockerClient())
    monitor = HealthMonitor()
    await monitor._poll_once(docker_service)
    await monitor._poll_once(docker_service)

    incidents = IncidentRepository(db_session)
    all_incidents = await incidents.list_all()
    assert len(all_incidents) == 1


async def test_poll_once_ignores_healthy_containers(db_session, monkeypatch):
    async def fake_list_containers(self, all=True):
        return [_HealthyContainer()]

    monkeypatch.setattr(DockerClient, "list_containers", fake_list_containers)

    docker_service = DockerMonitoringService(DockerClient())
    monitor = HealthMonitor()
    await monitor._poll_once(docker_service)

    incidents = IncidentRepository(db_session)
    assert await incidents.list_all() == []


class _RestartingContainer:
    """A container Docker is actively restarting after each crash - reports
    running=True/status=running between crashes, so _is_collapsed alone
    would never catch it. Only a climbing restart_count reveals the loop."""

    id = "loopy1"
    short_id = "loopy1"
    name = "loopy"
    status = "running"

    def __init__(self, restart_count: int):
        self.attrs = {
            "State": {"Status": "running", "Running": True},
            "Created": "2026-07-01T09:59:00.000000000Z",
            "RestartCount": restart_count,
            "Config": {"Image": "sentinel/loopy:latest", "Cmd": ["run"]},
            "NetworkSettings": {"Ports": {}},
            "Mounts": [],
        }


async def test_poll_once_does_not_flag_restart_count_on_first_sighting(db_session, monkeypatch):
    """A container already at restart_count=5 the first time the monitor
    ever sees it is old history, not a fresh crash - must not open an
    incident purely from the baseline observation."""

    async def fake_list_containers(self, all=True):
        return [_RestartingContainer(restart_count=5)]

    monkeypatch.setattr(DockerClient, "list_containers", fake_list_containers)

    docker_service = DockerMonitoringService(DockerClient())
    monitor = HealthMonitor()
    await monitor._poll_once(docker_service)

    incidents = IncidentRepository(db_session)
    assert await incidents.list_all() == []


async def test_poll_once_detects_restart_count_increase_as_collapse(db_session, monkeypatch):
    _patch_docker(monkeypatch, FakeContainer())  # for the incident's own container fetch during analysis
    _patch_continuum(monkeypatch, response=SAMPLE_DIAGNOSIS)

    calls = {"count": 5}

    async def fake_list_containers(self, all=True):
        return [_RestartingContainer(restart_count=calls["count"])]

    monkeypatch.setattr(DockerClient, "list_containers", fake_list_containers)

    async def fake_post_message(self, text, blocks=None):
        return None

    monkeypatch.setattr(SlackClient, "post_message", fake_post_message)

    docker_service = DockerMonitoringService(DockerClient())
    monitor = HealthMonitor()
    await monitor._poll_once(docker_service)  # baseline - restart_count=5, no incident
    incidents = IncidentRepository(db_session)
    assert await incidents.list_all() == []

    calls["count"] = 6  # a fresh crash happened between polls
    await monitor._poll_once(docker_service)
    all_incidents = await incidents.list_all()
    assert len(all_incidents) == 1
