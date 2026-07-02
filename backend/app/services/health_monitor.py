"""Background poller that turns a collapsed Docker container into a fully
handled incident with no human action: detect -> open incident -> analyze
(root cause + severity) -> Slack alert. Runs as a single asyncio task for the
lifetime of the app process, started/stopped from app/main.py's lifespan.

Reuses IncidentService/DockerMonitoringService/RootCauseAnalysisService
exactly as the manual API path (POST /incidents, POST /incidents/{id}/analyze)
does - this module only decides *when* to call them, never duplicates their
logic. Each poll tick builds its own DB session and Continuum client, the
same pattern app/api/frontend/development.py's background compare job uses,
since nothing here runs inside a request's Depends() scope."""

import asyncio

from app.config.settings import get_settings
from app.continuum.client import ContinuumClient
from app.continuum.registry import get_global_registry
from app.core.logging import get_logger
from app.database.session import AsyncSessionLocal
from app.integrations.docker.client import DockerClient
from app.integrations.docker.schemas import ContainerHealthStatus, ContainerSummary
from app.integrations.docker.service import DockerMonitoringService
from app.integrations.slack.client import SlackClient
from app.repositories.incident_repository import IncidentRepository
from app.schemas.incident import IncidentCreateRequest
from app.services.incident_service import IncidentService
from app.services.root_cause_service import RootCauseAnalysisService

logger = get_logger(__name__)

# A container that's still starting up isn't "collapsed" - only a stopped
# container is. Combined with the health field (which covers containers with
# a Docker HEALTHCHECK directive that are still reported as "running").
_COLLAPSED_STATUSES = {"exited", "dead"}


def _is_collapsed(container: ContainerSummary) -> bool:
    if container.health == ContainerHealthStatus.UNHEALTHY:
        return True
    return (not container.running) and container.status in _COLLAPSED_STATUSES


class HealthMonitor:
    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self._last_restart_count: dict[str, int] = {}

    def _restart_count_increased(self, container: ContainerSummary) -> bool:
        """Catches a Docker-managed restart loop (--restart=on-failure/always)
        that _is_collapsed alone misses: Docker keeps restarting the process
        for you, so between crashes the container reports status=running,
        never exited/dead. Only a poll-to-poll increase in restart_count
        reveals a fresh crash - a static high restart_count could just as
        easily be old history from before the monitor started (or from an
        already-resolved incident) rather than an active problem, so this is
        deliberately stateful rather than a threshold check."""
        previous = self._last_restart_count.get(container.id)
        self._last_restart_count[container.id] = container.restart_count
        return previous is not None and container.restart_count > previous

    def start(self) -> None:
        if not get_settings().health_monitor_enabled:
            logger.info("health_monitor_disabled")
            return
        self._task = asyncio.create_task(self._run())
        logger.info("health_monitor_started")

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None

    async def _run(self) -> None:
        docker_service = DockerMonitoringService(DockerClient())
        while True:
            try:
                await self._poll_once(docker_service)
            except Exception as exc:  # noqa: BLE001 - one bad tick must never kill the loop
                logger.warning("health_monitor_poll_failed", extra={"error": str(exc)})
            await asyncio.sleep(get_settings().health_monitor_interval_seconds)

    async def _poll_once(self, docker_service: DockerMonitoringService) -> None:
        containers = await docker_service.list_containers()
        collapsed = [c for c in containers if _is_collapsed(c) or self._restart_count_increased(c)]
        if not collapsed:
            return

        settings = get_settings()
        async with AsyncSessionLocal() as db:
            incidents = IncidentRepository(db)
            continuum_client = ContinuumClient(registry=get_global_registry())
            slack_client = SlackClient(settings.slack_webhook_url)
            root_cause_service = RootCauseAnalysisService(docker_service, continuum_client)
            service = IncidentService(incidents, docker_service, root_cause_service, slack_client)

            for container in collapsed:
                existing = await incidents.find_active_incident_for_container(container.id)
                if existing is not None:
                    continue

                logger.info(
                    "health_monitor_detected_collapse",
                    extra={"container": container.name, "status": container.status},
                )
                incident = await service.create_incident(
                    IncidentCreateRequest(
                        title=f"{container.name} is {container.status}",
                        container_ids=[container.id],
                    )
                )
                await db.commit()

                try:
                    await service.analyze_incident(incident.id)
                    await db.commit()
                except Exception as exc:  # noqa: BLE001 - a bad analysis shouldn't skip other collapsed containers
                    logger.warning(
                        "health_monitor_analysis_failed",
                        extra={"incident_id": str(incident.id), "error": str(exc)},
                    )


_monitor = HealthMonitor()


def get_health_monitor() -> HealthMonitor:
    return _monitor
