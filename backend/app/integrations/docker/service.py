import re
import time
from datetime import datetime
from typing import Any

from app.core.exceptions import ForbiddenError, GatewayTimeoutError, NotFoundError, ServiceUnavailableError
from app.core.logging import get_logger
from app.integrations.docker.client import DockerClient
from app.integrations.docker.exceptions import (
    DockerContainerNotFoundError,
    DockerError,
    DockerPermissionError,
    DockerTimeoutError,
)
from app.integrations.docker.schemas import (
    BlockIOStats,
    ContainerDetail,
    ContainerHealthStatus,
    ContainerLogEntry,
    ContainerLogs,
    ContainerStats,
    ContainerSummary,
    NetworkStats,
    PortMapping,
    VolumeMount,
)
from app.utils.time import utc_now

logger = get_logger(__name__)

_DOCKER_TS_RE = re.compile(r"^(?P<base>.+?)(?:\.(?P<frac>\d+))?(?P<tz>Z|[+-]\d{2}:\d{2})$")
_ZERO_TIME_PREFIX = "0001-01-01"


def _parse_docker_time(value: str | None) -> datetime | None:
    """Docker timestamps are RFC3339Nano; Python's fromisoformat only accepts
    up to microsecond precision, and Docker uses the zero-value 0001-01-01
    to mean "never happened" (e.g. a container that was created but never
    started). Returns None for both the zero-value and anything unparseable
    rather than raising - this is metadata enrichment, not critical path."""
    if not value or value.startswith(_ZERO_TIME_PREFIX):
        return None
    match = _DOCKER_TS_RE.match(value)
    if not match:
        return None
    base = match.group("base")
    frac = (match.group("frac") or "0").ljust(6, "0")[:6]
    tz = match.group("tz")
    tz = "+00:00" if tz == "Z" else tz
    try:
        return datetime.fromisoformat(f"{base}.{frac}{tz}")
    except ValueError:
        return None


def _image_tag(attrs: dict) -> str:
    return (attrs.get("Config") or {}).get("Image", "unknown")


def _parse_ports(attrs: dict) -> list[PortMapping]:
    ports_map = (attrs.get("NetworkSettings") or {}).get("Ports") or {}
    result: list[PortMapping] = []
    for key, bindings in ports_map.items():
        port_str, _, proto = key.partition("/")
        try:
            container_port = int(port_str)
        except ValueError:
            continue
        if not bindings:
            result.append(PortMapping(container_port=container_port, protocol=proto or "tcp"))
            continue
        for binding in bindings:
            result.append(
                PortMapping(
                    container_port=container_port,
                    protocol=proto or "tcp",
                    host_ip=binding.get("HostIp"),
                    host_port=int(binding["HostPort"]) if binding.get("HostPort") else None,
                )
            )
    return result


def _parse_mounts(attrs: dict) -> list[VolumeMount]:
    mounts = attrs.get("Mounts") or []
    return [
        VolumeMount(
            source=m.get("Source", ""),
            destination=m.get("Destination", ""),
            mode=m.get("Mode") or ("rw" if m.get("RW", True) else "ro"),
            type=m.get("Type", "volume"),
        )
        for m in mounts
    ]


def _calculate_cpu_percent(stats: dict) -> float:
    cpu_stats = stats.get("cpu_stats") or {}
    precpu_stats = stats.get("precpu_stats") or {}
    cpu_total = (cpu_stats.get("cpu_usage") or {}).get("total_usage", 0)
    precpu_total = (precpu_stats.get("cpu_usage") or {}).get("total_usage", 0)
    cpu_delta = cpu_total - precpu_total
    system_delta = (cpu_stats.get("system_cpu_usage", 0)) - (precpu_stats.get("system_cpu_usage", 0))
    online_cpus = cpu_stats.get("online_cpus") or len((cpu_stats.get("cpu_usage") or {}).get("percpu_usage") or []) or 1
    if system_delta > 0 and cpu_delta > 0:
        return round((cpu_delta / system_delta) * online_cpus * 100.0, 2)
    return 0.0


def _calculate_memory(stats: dict) -> tuple[int, int, float]:
    memory_stats = stats.get("memory_stats") or {}
    usage = memory_stats.get("usage", 0)
    inner_stats = memory_stats.get("stats") or {}
    cache = inner_stats.get("cache") or inner_stats.get("inactive_file") or 0
    adjusted_usage = max(usage - cache, 0)
    limit = memory_stats.get("limit", 0)
    percent = round((adjusted_usage / limit) * 100, 2) if limit else 0.0
    return adjusted_usage, limit, percent


def _calculate_network(stats: dict) -> NetworkStats:
    networks = stats.get("networks") or {}
    rx_bytes = sum(iface.get("rx_bytes", 0) for iface in networks.values())
    tx_bytes = sum(iface.get("tx_bytes", 0) for iface in networks.values())
    return NetworkStats(rx_bytes=rx_bytes, tx_bytes=tx_bytes)


def _calculate_block_io(stats: dict) -> BlockIOStats:
    entries = (stats.get("blkio_stats") or {}).get("io_service_bytes_recursive") or []
    read_bytes = sum(e.get("value", 0) for e in entries if (e.get("op") or "").lower() == "read")
    write_bytes = sum(e.get("value", 0) for e in entries if (e.get("op") or "").lower() == "write")
    return BlockIOStats(read_bytes=read_bytes, write_bytes=write_bytes)


class DockerMonitoringService:
    """Collects live production state from the local Docker Engine. This is
    a pure data-collection layer, deliberately not routed through Continuum
    - no AI reasoning happens here. Everything is fetched live; nothing is
    persisted. Schemas are shaped for the future Root Cause Analysis Agent
    to consume directly."""

    def __init__(self, client: DockerClient) -> None:
        self.client = client

    async def list_containers(self) -> list[ContainerSummary]:
        containers = await self._call(self.client.list_containers, all=True)
        return [self._to_summary(c) for c in containers]

    async def get_container(self, container_id: str) -> ContainerDetail:
        container = await self._call(self.client.get_container, container_id)
        raw_stats: dict | None
        try:
            raw_stats = await self.client.container_stats(container.id)
        except DockerError:
            raw_stats = None  # metadata is still useful even if a stats snapshot momentarily fails
        return self._to_detail(container, raw_stats)

    async def get_container_stats(self, container_id: str) -> ContainerStats:
        container = await self._call(self.client.get_container, container_id)
        raw_stats = await self._call(self.client.container_stats, container.id)
        return self._parse_stats(container.id, raw_stats)

    async def get_container_logs(
        self, container_id: str, tail: int, timestamps: bool, limit: int
    ) -> ContainerLogs:
        container = await self._call(self.client.get_container, container_id)
        raw = await self._call(self.client.container_logs, container.id, tail=tail, timestamps=timestamps)
        return self._parse_logs(container.id, raw, limit)

    async def restart_container(self, container_id: str, timeout: int = 10) -> None:
        start = time.perf_counter()
        container = await self._call(self.client.get_container, container_id)
        await self._call(self.client.restart_container, container.id, timeout=timeout)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            "container_restarted",
            extra={"container_id": container.id, "duration_ms": duration_ms},
        )

    async def health(self) -> bool:
        return await self._call(self.client.health)

    @staticmethod
    def _to_summary(container: Any) -> ContainerSummary:
        attrs = container.attrs
        state = attrs.get("State") or {}
        health_raw = (state.get("Health") or {}).get("Status")
        return ContainerSummary(
            id=container.id,
            short_id=container.short_id,
            name=container.name,
            image=_image_tag(attrs),
            status=state.get("Status", getattr(container, "status", "unknown")),
            health=ContainerHealthStatus(health_raw) if health_raw else ContainerHealthStatus.NONE,
            running=bool(state.get("Running", False)),
            created_at=_parse_docker_time(attrs.get("Created")),
            started_at=_parse_docker_time(state.get("StartedAt")),
            restart_count=attrs.get("RestartCount", 0),
            exposed_ports=_parse_ports(attrs),
        )

    @classmethod
    def _to_detail(cls, container: Any, raw_stats: dict | None) -> ContainerDetail:
        summary = cls._to_summary(container)
        attrs = container.attrs
        return ContainerDetail(
            **summary.model_dump(),
            command=" ".join((attrs.get("Config") or {}).get("Cmd") or []) or None,
            mounted_volumes=_parse_mounts(attrs),
            stats=cls._parse_stats(container.id, raw_stats) if raw_stats else None,
        )

    @staticmethod
    def _parse_stats(container_id: str, raw: dict) -> ContainerStats:
        usage, limit, percent = _calculate_memory(raw)
        return ContainerStats(
            container_id=container_id,
            cpu_usage_percent=_calculate_cpu_percent(raw),
            memory_usage_bytes=usage,
            memory_limit_bytes=limit,
            memory_usage_percent=percent,
            network=_calculate_network(raw),
            block_io=_calculate_block_io(raw),
            collected_at=utc_now(),
        )

    @staticmethod
    def _parse_logs(container_id: str, raw: bytes, limit: int) -> ContainerLogs:
        text = raw.decode("utf-8", errors="replace")
        raw_lines = [line for line in text.split("\n") if line]
        lines: list[ContainerLogEntry] = []
        for line in raw_lines:
            parts = line.split(" ", 1)
            timestamp = _parse_docker_time(parts[0]) if len(parts) == 2 else None
            message = parts[1] if timestamp is not None and len(parts) == 2 else line
            lines.append(ContainerLogEntry(timestamp=timestamp, message=message))
        truncated = len(lines) > limit
        if truncated:
            lines = lines[-limit:]
        return ContainerLogs(container_id=container_id, lines=lines, truncated=truncated)

    @staticmethod
    async def _call(fn, *args, **kwargs):
        try:
            return await fn(*args, **kwargs)
        except DockerContainerNotFoundError as exc:
            raise NotFoundError(str(exc)) from exc
        except DockerPermissionError as exc:
            raise ForbiddenError(str(exc)) from exc
        except DockerTimeoutError as exc:
            raise GatewayTimeoutError(str(exc)) from exc
        except DockerError as exc:
            raise ServiceUnavailableError(f"Docker daemon error: {exc}") from exc
