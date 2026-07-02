from datetime import datetime, timedelta, timezone

from app.integrations.docker.dependencies import get_docker_service
from app.integrations.docker.schemas import (
    ContainerHealthStatus,
    ContainerLogEntry,
    ContainerLogs,
    ContainerStats,
    ContainerSummary,
    NetworkStats,
    BlockIOStats,
)
from app.main import app
from app.models.incident import Incident, IncidentContainer
from tests.test_github import _register_and_login

NOW = datetime.now(timezone.utc)


class FakeDockerService:
    def __init__(self, containers, logs_by_id=None, stats_by_id=None):
        self._containers = containers
        self._logs_by_id = logs_by_id or {}
        self._stats_by_id = stats_by_id or {}

    async def list_containers(self):
        return self._containers

    async def get_container_stats(self, container_id):
        return self._stats_by_id[container_id]

    async def get_container_logs(self, container_id, tail, timestamps, limit):
        return self._logs_by_id.get(container_id, ContainerLogs(container_id=container_id, lines=[]))


def _make_container(container_id, name, health, running=True, restart_count=0):
    return ContainerSummary(
        id=container_id,
        short_id=container_id[:12],
        name=name,
        image="app:latest",
        status="running" if running else "exited",
        health=health,
        running=running,
        created_at=NOW - timedelta(days=14),
        started_at=NOW - timedelta(days=14, hours=-6),
        restart_count=restart_count,
    )


def _make_stats(container_id, cpu=34.0, memory=58.0):
    return ContainerStats(
        container_id=container_id,
        cpu_usage_percent=cpu,
        memory_usage_bytes=1000,
        memory_limit_bytes=2000,
        memory_usage_percent=memory,
        network=NetworkStats(rx_bytes=0, tx_bytes=0),
        block_io=BlockIOStats(read_bytes=0, write_bytes=0),
        collected_at=NOW,
    )


async def test_production_summary_shapes_containers_and_logs(client):
    healthy = _make_container("aaa111", "api-gateway", ContainerHealthStatus.HEALTHY)
    unhealthy = _make_container("bbb222", "media-transcoder", ContainerHealthStatus.UNHEALTHY, restart_count=3)

    logs = ContainerLogs(
        container_id="bbb222",
        lines=[ContainerLogEntry(timestamp=NOW, message="ERROR OOMKilled: container ran out of memory")],
    )

    fake_service = FakeDockerService(
        containers=[healthy, unhealthy],
        logs_by_id={"bbb222": logs},
        stats_by_id={"aaa111": _make_stats("aaa111", 34, 58), "bbb222": _make_stats("bbb222", 90, 95)},
    )
    app.dependency_overrides[get_docker_service] = lambda: fake_service

    try:
        headers = await _register_and_login(client)
        response = await client.get("/api/production-intelligence/summary", headers=headers)
    finally:
        app.dependency_overrides.pop(get_docker_service, None)

    assert response.status_code == 200
    body = response.json()

    assert body["stats"]["containersTotal"] == 2
    assert body["stats"]["containersHealthy"] == 1

    container_by_name = {c["name"]: c for c in body["containers"]}
    assert container_by_name["api-gateway"]["status"] == "healthy"
    assert container_by_name["api-gateway"]["cpuPercent"] == 34
    assert container_by_name["media-transcoder"]["status"] == "unhealthy"
    assert container_by_name["media-transcoder"]["restarts"] == 3

    assert len(body["logs"]) == 1
    assert body["logs"][0]["level"] == "error"
    assert body["logs"][0]["service"] == "media-transcoder"
    assert "OOMKilled" in body["logs"][0]["message"]


async def test_production_summary_maps_incident_severity_and_status(client, db_session):
    fake_service = FakeDockerService(containers=[])
    app.dependency_overrides[get_docker_service] = lambda: fake_service

    incident = Incident(
        title="notifications service degraded",
        summary="",
        severity="critical",
        status="recovery_available",
        recovery_executed=False,
    )
    incident.affected_containers.append(
        IncidentContainer(container_id="ccc333", container_name="notifications", image="notifications:latest")
    )
    db_session.add(incident)
    await db_session.commit()

    try:
        headers = await _register_and_login(client)
        response = await client.get("/api/production-intelligence/summary", headers=headers)
    finally:
        app.dependency_overrides.pop(get_docker_service, None)

    assert response.status_code == 200
    body = response.json()

    assert len(body["incidents"]) == 1
    item = body["incidents"][0]
    assert item["service"] == "notifications"
    assert item["severity"] == "sev1"
    assert item["status"] == "monitoring"
    assert body["stats"]["openIncidents"] == 1


async def test_production_summary_requires_auth(client):
    response = await client.get("/api/production-intelligence/summary")
    assert response.status_code == 401


async def test_production_summary_with_no_containers_or_incidents(client):
    fake_service = FakeDockerService(containers=[])
    app.dependency_overrides[get_docker_service] = lambda: fake_service

    try:
        headers = await _register_and_login(client)
        response = await client.get("/api/production-intelligence/summary", headers=headers)
    finally:
        app.dependency_overrides.pop(get_docker_service, None)

    assert response.status_code == 200
    body = response.json()
    assert body["containers"] == []
    assert body["logs"] == []
    assert body["incidents"] == []
    assert body["stats"]["containersTotal"] == 0
