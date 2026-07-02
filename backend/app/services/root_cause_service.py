import time

from app.agents.production.schemas import IncidentDiagnosis, RootCauseAnalysisInput, RootCauseAnalysisResponse
from app.continuum.client import ContinuumClient
from app.continuum.exceptions import AgentNotFoundError
from app.core.exceptions import AppException, GatewayTimeoutError, ServiceUnavailableError, ValidationAppError
from app.core.logging import get_logger
from app.integrations.docker.service import DockerMonitoringService

logger = get_logger(__name__)

_LOG_TAIL = 200


class RootCauseAnalysisService:
    """Diagnosis only - reuses DockerMonitoringService entirely for Docker
    access (never touches DockerClient directly) and ContinuumClient for the
    AI call. Never restarts anything; that's a future Safe Recovery phase."""

    def __init__(self, docker_service: DockerMonitoringService, continuum_client: ContinuumClient) -> None:
        self.docker_service = docker_service
        self.continuum_client = continuum_client

    async def analyze_container(self, container_id: str) -> RootCauseAnalysisResponse:
        """The original, full-detail diagnosis - backs the on-demand
        POST /docker/containers/{id}/analyze endpoint."""
        return await self._run_agent(container_id, "root_cause", RootCauseAnalysisResponse)

    async def diagnose_incident(self, container_id: str) -> IncidentDiagnosis:
        """A smaller/faster diagnosis for the health monitor's automatic
        incident path - see IncidentDiagnosis's docstring for why this
        exists as a separate agent rather than reusing analyze_container."""
        return await self._run_agent(container_id, "incident_diagnosis", IncidentDiagnosis)

    async def _run_agent(self, container_id: str, agent_name: str, response_type: type):
        overall_start = time.perf_counter()

        docker_start = time.perf_counter()
        container = await self.docker_service.get_container(container_id)
        logs = await self.docker_service.get_container_logs(
            container_id, tail=_LOG_TAIL, timestamps=True, limit=_LOG_TAIL
        )
        docker_collection_ms = round((time.perf_counter() - docker_start) * 1000, 2)

        agent_input = RootCauseAnalysisInput(container=container, logs=logs)

        try:
            result = await self.continuum_client.run_agent(agent_name, agent_input)
        except AgentNotFoundError as exc:
            raise ServiceUnavailableError("Root cause analysis is not currently available") from exc

        total_duration_ms = round((time.perf_counter() - overall_start) * 1000, 2)

        logger.info(
            f"{agent_name}_completed" if result.success else f"{agent_name}_failed",
            extra={
                "container_id": container_id,
                "docker_collection_ms": docker_collection_ms,
                "continuum_latency_ms": result.duration_ms,
                "total_duration_ms": total_duration_ms,
                "success": result.success,
            },
        )

        if not result.success:
            raise self._map_agent_failure(result.error_type, result.error)

        response = result.data
        assert isinstance(response, response_type)
        return response

    @staticmethod
    def _map_agent_failure(error_type: str | None, message: str | None) -> AppException:
        message = message or "Root cause analysis failed for an unknown reason"
        if error_type == "MalformedResponseError":
            return ValidationAppError(f"The AI returned a response that couldn't be parsed: {message}")
        if error_type == "ContinuumTimeoutError":
            return GatewayTimeoutError("The AI provider timed out. Please try again.")
        if error_type in ("ContinuumUnavailableError", "ContinuumConfigurationError"):
            return ServiceUnavailableError("The AI provider is currently unavailable.")
        return ServiceUnavailableError(f"Root cause analysis failed: {message}")
