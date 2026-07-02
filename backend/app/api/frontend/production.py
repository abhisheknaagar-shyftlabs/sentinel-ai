from datetime import timezone

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.deps import get_db
from app.integrations.docker.dependencies import get_docker_service
from app.integrations.docker.schemas import ContainerHealthStatus, ContainerSummary
from app.integrations.docker.service import DockerMonitoringService
from app.models.incident import Incident
from app.models.user import User
from app.repositories.incident_repository import IncidentRepository
from app.schemas.camel import CamelModel
from app.schemas.incident import IncidentStatus
from app.security.dependencies import get_current_user
from app.utils.time import format_clock_time, format_duration_since, format_relative_time, utc_now

router = APIRouter(prefix="/production-intelligence", tags=["frontend-production"])

_MAX_LOG_LINES_PER_CONTAINER = 5
_MAX_LOGS_IN_SUMMARY = 20

_SEVERITY_TO_SEV = {"critical": "sev1", "high": "sev2", "medium": "sev3", "low": "sev4"}
_STATUS_TO_CONTRACT = {
    IncidentStatus.OPEN.value: "open",
    IncidentStatus.INVESTIGATING.value: "investigating",
    IncidentStatus.ANALYZED.value: "monitoring",
    IncidentStatus.RECOVERY_AVAILABLE.value: "monitoring",
    IncidentStatus.RESOLVED.value: "resolved",
}


class Trend(CamelModel):
    direction: str
    change_percent: float
    is_positive: bool


class ProdStats(CamelModel):
    containers_healthy: int
    containers_total: int
    open_incidents: int
    open_incidents_trend: Trend
    auto_recoveries_today: int
    avg_recovery_time_minutes: float
    avg_recovery_trend: Trend


class ContainerItem(CamelModel):
    id: str
    name: str
    status: str
    cpu_percent: int
    memory_percent: int
    uptime: str
    restarts: int


class LogItem(CamelModel):
    id: str
    timestamp: str
    level: str
    service: str
    message: str


class IncidentItem(CamelModel):
    id: str
    title: str
    service: str
    severity: str
    status: str
    root_cause: str | None = None
    auto_recovered: bool
    started_at: str


class ProdSummaryResponse(CamelModel):
    stats: ProdStats
    containers: list[ContainerItem]
    logs: list[LogItem]
    incidents: list[IncidentItem]


def _map_container_status(container: ContainerSummary) -> str:
    if not container.running:
        return "unhealthy"
    if container.health == ContainerHealthStatus.HEALTHY:
        return "healthy"
    if container.health == ContainerHealthStatus.UNHEALTHY:
        return "unhealthy"
    if container.health == ContainerHealthStatus.STARTING:
        return "degraded"
    return "unknown"  # no healthcheck configured, but running


def _infer_log_level(message: str) -> str:
    upper = message.upper()
    if "FATAL" in upper or "ERROR" in upper:
        return "error"
    if "WARN" in upper:
        return "warn"
    if "DEBUG" in upper:
        return "debug"
    return "info"


def _incident_service_name(incident: Incident) -> str:
    if incident.affected_containers:
        return incident.affected_containers[0].container_name
    return "unknown"


def _as_utc(dt):
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


@router.get("/summary", response_model=ProdSummaryResponse)
async def get_summary(
    current_user: User = Depends(get_current_user),
    docker_service: DockerMonitoringService = Depends(get_docker_service),
    db: AsyncSession = Depends(get_db),
):
    containers = await docker_service.list_containers()

    container_items: list[ContainerItem] = []
    log_items: list[LogItem] = []
    for container in containers:
        try:
            stats = await docker_service.get_container_stats(container.id)
            cpu_percent = round(stats.cpu_usage_percent)
            memory_percent = round(stats.memory_usage_percent)
        except Exception:  # noqa: BLE001 - a stats hiccup shouldn't break the whole summary
            cpu_percent = 0
            memory_percent = 0

        container_items.append(
            ContainerItem(
                id=container.short_id,
                name=container.name,
                status=_map_container_status(container),
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                uptime=format_duration_since(container.started_at),
                restarts=container.restart_count,
            )
        )

        if container.running:
            try:
                logs = await docker_service.get_container_logs(
                    container.id, tail=_MAX_LOG_LINES_PER_CONTAINER, timestamps=True, limit=_MAX_LOG_LINES_PER_CONTAINER
                )
            except Exception:  # noqa: BLE001
                logs = None
            if logs:
                for line in logs.lines:
                    log_items.append(
                        LogItem(
                            id=f"{container.short_id}-{line.timestamp or utc_now().isoformat()}",
                            timestamp=format_clock_time(line.timestamp),
                            level=_infer_log_level(line.message),
                            service=container.name,
                            message=line.message,
                        )
                    )

    log_items.sort(key=lambda item: item.timestamp, reverse=True)
    log_items = log_items[:_MAX_LOGS_IN_SUMMARY]

    healthy_count = sum(1 for c in container_items if c.status == "healthy")

    incidents = await IncidentRepository(db).list_all(limit=200)
    incident_items = [
        IncidentItem(
            id=str(incident.id),
            title=incident.title,
            service=_incident_service_name(incident),
            severity=_SEVERITY_TO_SEV.get(incident.severity, "sev4"),
            status=_STATUS_TO_CONTRACT.get(incident.status, "open"),
            root_cause=incident.root_cause_summary,
            auto_recovered=incident.recovery_executed,
            started_at=format_relative_time(incident.created_at),
        )
        for incident in incidents
    ]

    open_incidents = sum(1 for i in incidents if i.status != IncidentStatus.RESOLVED.value)

    resolved_and_recovered = [
        i for i in incidents if i.recovery_executed and i.resolved_at is not None
    ]
    today = utc_now().date()
    auto_recoveries_today = sum(
        1 for i in resolved_and_recovered if _as_utc(i.resolved_at).date() == today
    )
    if resolved_and_recovered:
        recovery_minutes = [
            (_as_utc(i.resolved_at) - _as_utc(i.created_at)).total_seconds() / 60
            for i in resolved_and_recovered
        ]
        avg_recovery_time_minutes = round(sum(recovery_minutes) / len(recovery_minutes), 1)
    else:
        avg_recovery_time_minutes = 0.0

    zero_trend = Trend(direction="flat", change_percent=0, is_positive=True)

    return ProdSummaryResponse(
        stats=ProdStats(
            containers_healthy=healthy_count,
            containers_total=len(container_items),
            open_incidents=open_incidents,
            open_incidents_trend=zero_trend,
            auto_recoveries_today=auto_recoveries_today,
            avg_recovery_time_minutes=avg_recovery_time_minutes,
            avg_recovery_trend=zero_trend,
        ),
        containers=container_items,
        logs=log_items,
        incidents=incident_items,
    )
