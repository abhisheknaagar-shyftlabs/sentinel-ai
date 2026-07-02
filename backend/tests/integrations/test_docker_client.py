import pytest
from docker.errors import APIError, NotFound

from app.integrations.docker.client import DockerClient
from app.integrations.docker.exceptions import DockerContainerNotFoundError, DockerUnavailableError


class FakeContainer:
    def __init__(self, container_id="abc123", name="web"):
        self.id = container_id
        self.short_id = container_id[:12]
        self.name = name
        self.status = "running"
        self.attrs = {"State": {"Status": "running", "Running": True}}
        self._stats = {"cpu_stats": {}, "precpu_stats": {}}

    def stats(self, stream=False):
        return self._stats

    def logs(self, tail, timestamps):
        return b"line one\nline two\n"

    def restart(self, timeout):
        self.restarted_with_timeout = timeout


class FakeContainers:
    def __init__(self, containers):
        self._containers = {c.id: c for c in containers}

    def list(self, all=True):
        return list(self._containers.values())

    def get(self, container_id):
        try:
            return self._containers[container_id]
        except KeyError:
            raise NotFound(f"No such container: {container_id}") from None


class FakeSDKClient:
    def __init__(self, containers=None, ping_ok=True, raise_on_ping=None):
        self.containers = FakeContainers(containers or [])
        self._ping_ok = ping_ok
        self._raise_on_ping = raise_on_ping

    def ping(self):
        if self._raise_on_ping:
            raise self._raise_on_ping
        return self._ping_ok


async def test_list_containers():
    fake = FakeSDKClient(containers=[FakeContainer("a"), FakeContainer("b")])
    client = DockerClient(docker_client=fake)
    containers = await client.list_containers()
    assert len(containers) == 2


async def test_get_container_not_found_raises():
    fake = FakeSDKClient(containers=[])
    client = DockerClient(docker_client=fake)
    with pytest.raises(DockerContainerNotFoundError):
        await client.get_container("missing")


async def test_get_container_success():
    fake = FakeSDKClient(containers=[FakeContainer("a")])
    client = DockerClient(docker_client=fake)
    container = await client.get_container("a")
    assert container.id == "a"


async def test_container_stats():
    fake = FakeSDKClient(containers=[FakeContainer("a")])
    client = DockerClient(docker_client=fake)
    stats = await client.container_stats("a")
    assert "cpu_stats" in stats


async def test_container_logs():
    fake = FakeSDKClient(containers=[FakeContainer("a")])
    client = DockerClient(docker_client=fake)
    logs = await client.container_logs("a", tail=100, timestamps=True)
    assert logs == b"line one\nline two\n"


async def test_restart_container():
    container = FakeContainer("a")
    fake = FakeSDKClient(containers=[container])
    client = DockerClient(docker_client=fake)
    await client.restart_container("a", timeout=5)
    assert container.restarted_with_timeout == 5


async def test_health_ok():
    fake = FakeSDKClient(ping_ok=True)
    client = DockerClient(docker_client=fake)
    assert await client.health() is True


async def test_health_daemon_unavailable_raises():
    fake = FakeSDKClient(raise_on_ping=APIError("daemon down"))
    client = DockerClient(docker_client=fake)
    with pytest.raises(DockerUnavailableError):
        await client.health()
