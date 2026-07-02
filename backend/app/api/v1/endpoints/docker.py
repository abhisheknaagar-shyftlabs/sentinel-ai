from fastapi import APIRouter, Depends, Query

from app.continuum.client import ContinuumClient
from app.continuum.dependencies import get_continuum_client
from app.core.responses import success_envelope
from app.integrations.docker.dependencies import get_docker_service
from app.integrations.docker.service import DockerMonitoringService
from app.models.user import User
from app.security.dependencies import get_current_user
from app.services.root_cause_service import RootCauseAnalysisService

router = APIRouter(prefix="/docker", tags=["docker"])


def get_root_cause_service(
    docker_service: DockerMonitoringService = Depends(get_docker_service),
    continuum_client: ContinuumClient = Depends(get_continuum_client),
) -> RootCauseAnalysisService:
    return RootCauseAnalysisService(docker_service, continuum_client)


@router.get(
    "/containers",
    summary="List every container on the local Docker Engine",
    description="Returns lightweight metadata (no live stats) for every container, running or stopped.",
)
async def list_containers(
    current_user: User = Depends(get_current_user),
    service: DockerMonitoringService = Depends(get_docker_service),
):
    containers = await service.list_containers()
    return success_envelope([c.model_dump(mode="json") for c in containers])


@router.get(
    "/containers/{container_id}",
    summary="Get detailed metadata for one container",
    description="Metadata, mounted volumes, and a live stats snapshot in a single call.",
)
async def get_container(
    container_id: str,
    current_user: User = Depends(get_current_user),
    service: DockerMonitoringService = Depends(get_docker_service),
):
    container = await service.get_container(container_id)
    return success_envelope(container.model_dump(mode="json"))


@router.get(
    "/containers/{container_id}/stats",
    summary="Get a live CPU/memory/network/IO snapshot for one container",
)
async def get_container_stats(
    container_id: str,
    current_user: User = Depends(get_current_user),
    service: DockerMonitoringService = Depends(get_docker_service),
):
    stats = await service.get_container_stats(container_id)
    return success_envelope(stats.model_dump(mode="json"))


@router.get(
    "/containers/{container_id}/logs",
    summary="Get recent logs for one container",
)
async def get_container_logs(
    container_id: str,
    tail: int = Query(100, ge=1, le=5000, description="Number of lines to fetch from Docker"),
    timestamps: bool = Query(True, description="Whether Docker should prefix each line with a timestamp"),
    limit: int = Query(100, ge=1, le=5000, description="Max number of lines to return in the response"),
    current_user: User = Depends(get_current_user),
    service: DockerMonitoringService = Depends(get_docker_service),
):
    logs = await service.get_container_logs(container_id, tail=tail, timestamps=timestamps, limit=limit)
    return success_envelope(logs.model_dump(mode="json"))


@router.post(
    "/containers/{container_id}/restart",
    summary="Safely restart a container",
    description="SIGTERM then SIGKILL after a grace period. Never kills, removes, or prunes.",
)
async def restart_container(
    container_id: str,
    current_user: User = Depends(get_current_user),
    service: DockerMonitoringService = Depends(get_docker_service),
):
    await service.restart_container(container_id)
    return success_envelope(None, "Container restarted")


@router.post(
    "/containers/{container_id}/analyze",
    summary="Run AI root cause analysis on a container",
    description=(
        "Collects the container's live metadata, stats, and recent logs (via the existing Docker "
        "Monitoring service - never a new Docker call) and runs them through the Continuum-orchestrated "
        "Root Cause Analysis agent. Diagnosis only - this never restarts, modifies, or removes anything."
    ),
)
async def analyze_container(
    container_id: str,
    current_user: User = Depends(get_current_user),
    service: RootCauseAnalysisService = Depends(get_root_cause_service),
):
    result = await service.analyze_container(container_id)
    return success_envelope(result.model_dump(mode="json"), "Root cause analysis completed")
