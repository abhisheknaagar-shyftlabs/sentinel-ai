import pytest
from docker.errors import NotFound

from app.core.exceptions import ForbiddenError, GatewayTimeoutError, NotFoundError, ServiceUnavailableError
from app.integrations.docker.exceptions import (
    DockerContainerNotFoundError,
    DockerPermissionError,
    DockerTimeoutError,
    DockerUnavailableError,
)
from app.integrations.docker.schemas import ContainerHealthStatus
from app.integrations.docker.service import DockerMonitoringService

FULL_ATTRS = {
    "State": {
        "Status": "running",
        "Running": True,
        "StartedAt": "2026-07-01T10:00:00.123456789Z",
        "Health": {"Status": "healthy"},
    },
    "Created": "2026-07-01T09:59:00.000000000Z",
    "RestartCount": 2,
    "Config": {"Image": "sentinel/web:latest", "Cmd": ["python", "app.py"]},
    "NetworkSettings": {
        "Ports": {
            "8000/tcp": [{"HostIp": "0.0.0.0", "HostPort": "8000"}],
            "9000/tcp": None,
        }
    },
    "Mounts": [
        {"Type": "bind", "Source": "/host/data", "Destination": "/data", "Mode": "rw", "RW": True},
    ],
}

STATS_SAMPLE = {
    "cpu_stats": {
        "cpu_usage": {"total_usage": 2_000_000_000},
        "system_cpu_usage": 100_000_000_000,
        "online_cpus": 4,
    },
    "precpu_stats": {
        "cpu_usage": {"total_usage": 1_000_000_000},
        "system_cpu_usage": 90_000_000_000,
    },
    "memory_stats": {"usage": 209_715_200, "limit": 1_073_741_824, "stats": {"cache": 10_485_760}},
    "networks": {
        "eth0": {"rx_bytes": 1000, "tx_bytes": 2000},
        "eth1": {"rx_bytes": 500, "tx_bytes": 250},
    },
    "blkio_stats": {
        "io_service_bytes_recursive": [
            {"op": "Read", "value": 4096},
            {"op": "Write", "value": 8192},
            {"op": "Read", "value": 1024},
        ]
    },
}


class FakeContainer:
    def __init__(self, container_id="abc123def456", name="web", attrs=None, stats=None, logs=b"", fail=None):
        self.id = container_id
        self.short_id = container_id[:12]
        self.name = name
        self.status = "running"
        self.attrs = attrs or FULL_ATTRS
        self._stats = stats or STATS_SAMPLE
        self._logs = logs
        self._fail = fail

    async def _maybe_fail(self):
        if self._fail:
            raise self._fail


class FakeDockerClient:
    def __init__(self, container=None, fail=None):
        self.container = container
        self._fail = fail

    async def list_containers(self, all=True):
        if self._fail:
            raise self._fail
        return [self.container] if self.container else []

    async def get_container(self, container_id):
        if self._fail:
            raise self._fail
        if self.container is None or self.container.id != container_id:
            raise DockerContainerNotFoundError(container_id)
        return self.container

    async def container_stats(self, container_id):
        if self._fail:
            raise self._fail
        return self.container._stats

    async def container_logs(self, container_id, tail, timestamps):
        if self._fail:
            raise self._fail
        return self.container._logs

    async def restart_container(self, container_id, timeout=10):
        if self._fail:
            raise self._fail

    async def health(self):
        if self._fail:
            raise self._fail
        return True


async def test_list_containers_maps_summary_fields():
    service = DockerMonitoringService(FakeDockerClient(container=FakeContainer()))
    containers = await service.list_containers()
    assert len(containers) == 1
    summary = containers[0]
    assert summary.image == "sentinel/web:latest"
    assert summary.health == ContainerHealthStatus.HEALTHY
    assert summary.running is True
    assert summary.restart_count == 2
    assert summary.started_at is not None
    assert any(p.host_port == 8000 for p in summary.exposed_ports)
    assert any(p.container_port == 9000 and p.host_port is None for p in summary.exposed_ports)


async def test_get_container_includes_mounts_and_stats():
    service = DockerMonitoringService(FakeDockerClient(container=FakeContainer()))
    detail = await service.get_container("abc123def456")
    assert detail.command == "python app.py"
    assert detail.mounted_volumes[0].destination == "/data"
    assert detail.stats is not None
    assert detail.stats.cpu_usage_percent > 0


async def test_get_container_stats_calculates_cpu_memory_network_blkio():
    service = DockerMonitoringService(FakeDockerClient(container=FakeContainer()))
    stats = await service.get_container_stats("abc123def456")

    # cpu: (2e9-1e9)/(100e9-90e9) * 4 * 100 = 40.0
    assert stats.cpu_usage_percent == 40.0
    # memory: usage - cache = 209715200 - 10485760 = 199229440; /1073741824 * 100
    assert stats.memory_usage_bytes == 199_229_440
    assert stats.memory_limit_bytes == 1_073_741_824
    assert stats.network.rx_bytes == 1500
    assert stats.network.tx_bytes == 2250
    assert stats.block_io.read_bytes == 5120
    assert stats.block_io.write_bytes == 8192


async def test_get_container_logs_parses_timestamps():
    logs = b"2026-07-01T10:00:00.000000000Z first line\n2026-07-01T10:00:01.000000000Z second line\n"
    service = DockerMonitoringService(FakeDockerClient(container=FakeContainer(logs=logs)))
    result = await service.get_container_logs("abc123def456", tail=100, timestamps=True, limit=100)
    assert len(result.lines) == 2
    assert result.lines[0].message == "first line"
    assert result.lines[0].timestamp is not None
    assert result.truncated is False


async def test_get_container_logs_respects_limit():
    logs = b"\n".join(f"line {i}".encode() for i in range(10)) + b"\n"
    service = DockerMonitoringService(FakeDockerClient(container=FakeContainer(logs=logs)))
    result = await service.get_container_logs("abc123def456", tail=100, timestamps=False, limit=3)
    assert len(result.lines) == 3
    assert result.truncated is True
    assert result.lines[-1].message == "line 9"


async def test_container_not_found_maps_to_app_not_found_error():
    service = DockerMonitoringService(FakeDockerClient(container=None))
    with pytest.raises(NotFoundError):
        await service.get_container("missing")


async def test_permission_denied_maps_to_forbidden():
    service = DockerMonitoringService(FakeDockerClient(fail=DockerPermissionError("denied")))
    with pytest.raises(ForbiddenError):
        await service.list_containers()


async def test_timeout_maps_to_gateway_timeout():
    service = DockerMonitoringService(FakeDockerClient(fail=DockerTimeoutError("slow")))
    with pytest.raises(GatewayTimeoutError):
        await service.list_containers()


async def test_daemon_unavailable_maps_to_service_unavailable():
    service = DockerMonitoringService(FakeDockerClient(fail=DockerUnavailableError("down")))
    with pytest.raises(ServiceUnavailableError):
        await service.list_containers()
