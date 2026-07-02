import pytest

from app.core.exceptions import NotFoundError
from app.integrations.docker.dependencies import get_docker_service
from app.integrations.docker.schemas import (
    ContainerDetail,
    ContainerHealthStatus,
    ContainerLogEntry,
    ContainerLogs,
    ContainerStats,
    ContainerSummary,
    NetworkStats,
    BlockIOStats,
)
from app.main import app
from app.utils.time import utc_now
from tests.test_github import _register_and_login

SUMMARY = ContainerSummary(
    id="abc123def456",
    short_id="abc123def456",
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


class FakeDockerService:
    def __init__(self, fail_not_found: bool = False):
        self.fail_not_found = fail_not_found
        self.restart_calls = []

    async def list_containers(self):
        return [SUMMARY]

    async def get_container(self, container_id):
        if self.fail_not_found:
            raise NotFoundError("Container not found")
        return ContainerDetail(**SUMMARY.model_dump(), command="python app.py", mounted_volumes=[], stats=None)

    async def get_container_stats(self, container_id):
        return ContainerStats(
            container_id=container_id,
            cpu_usage_percent=12.5,
            memory_usage_bytes=1000,
            memory_limit_bytes=2000,
            memory_usage_percent=50.0,
            network=NetworkStats(rx_bytes=1, tx_bytes=2),
            block_io=BlockIOStats(read_bytes=3, write_bytes=4),
            collected_at=utc_now(),
        )

    async def get_container_logs(self, container_id, tail, timestamps, limit):
        return ContainerLogs(
            container_id=container_id,
            lines=[ContainerLogEntry(timestamp=None, message="hello")],
            truncated=False,
        )

    async def restart_container(self, container_id, timeout=10):
        self.restart_calls.append(container_id)


@pytest.fixture
def fake_docker_service():
    service = FakeDockerService()
    app.dependency_overrides[get_docker_service] = lambda: service
    yield service
    app.dependency_overrides.pop(get_docker_service, None)


async def test_list_containers(client, fake_docker_service):
    headers = await _register_and_login(client)
    response = await client.get("/api/v1/docker/containers", headers=headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 1
    assert data[0]["image"] == "sentinel/web:latest"


async def test_get_container(client, fake_docker_service):
    headers = await _register_and_login(client)
    response = await client.get("/api/v1/docker/containers/abc123def456", headers=headers)
    assert response.status_code == 200
    assert response.json()["data"]["command"] == "python app.py"


async def test_get_container_not_found(client, fake_docker_service):
    fake_docker_service.fail_not_found = True
    headers = await _register_and_login(client)
    response = await client.get("/api/v1/docker/containers/missing", headers=headers)
    assert response.status_code == 404


async def test_get_container_stats(client, fake_docker_service):
    headers = await _register_and_login(client)
    response = await client.get("/api/v1/docker/containers/abc123def456/stats", headers=headers)
    assert response.status_code == 200
    assert response.json()["data"]["cpu_usage_percent"] == 12.5


async def test_get_container_logs(client, fake_docker_service):
    headers = await _register_and_login(client)
    response = await client.get(
        "/api/v1/docker/containers/abc123def456/logs?tail=50&timestamps=false&limit=10",
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["data"]["lines"][0]["message"] == "hello"


async def test_restart_container(client, fake_docker_service):
    headers = await _register_and_login(client)
    response = await client.post("/api/v1/docker/containers/abc123def456/restart", headers=headers)
    assert response.status_code == 200
    assert fake_docker_service.restart_calls == ["abc123def456"]


async def test_unauthenticated_requests_rejected(client, fake_docker_service):
    response = await client.get("/api/v1/docker/containers")
    assert response.status_code == 401
