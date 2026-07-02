from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class ContainerHealthStatus(str, Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    STARTING = "starting"
    NONE = "none"  # no healthcheck configured on the container


class PortMapping(BaseModel):
    container_port: int
    protocol: str
    host_ip: str | None = None
    host_port: int | None = None


class VolumeMount(BaseModel):
    source: str
    destination: str
    mode: str
    type: str


class ContainerSummary(BaseModel):
    """Lightweight metadata for listing containers - no live stats, safe to
    call for every container without materially slowing down the response."""

    id: str
    short_id: str
    name: str
    image: str
    status: str
    health: ContainerHealthStatus
    running: bool
    created_at: datetime | None
    started_at: datetime | None
    restart_count: int
    exposed_ports: list[PortMapping] = Field(default_factory=list)


class ContainerDetail(ContainerSummary):
    """Everything in ContainerSummary plus mounts and a live stats snapshot -
    designed so the future Root Cause Analysis Agent can consume a single
    call for full runtime context on one container."""

    command: str | None = None
    mounted_volumes: list[VolumeMount] = Field(default_factory=list)
    stats: "ContainerStats | None" = None


class NetworkStats(BaseModel):
    rx_bytes: int
    tx_bytes: int


class BlockIOStats(BaseModel):
    read_bytes: int
    write_bytes: int


class ContainerStats(BaseModel):
    container_id: str
    cpu_usage_percent: float
    memory_usage_bytes: int
    memory_limit_bytes: int
    memory_usage_percent: float
    network: NetworkStats
    block_io: BlockIOStats
    collected_at: datetime


class ContainerLogEntry(BaseModel):
    timestamp: datetime | None
    message: str


class ContainerLogs(BaseModel):
    container_id: str
    lines: list[ContainerLogEntry] = Field(default_factory=list)
    truncated: bool = False


ContainerDetail.model_rebuild()
