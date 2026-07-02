from fastapi import Depends

from app.integrations.docker.client import DockerClient
from app.integrations.docker.service import DockerMonitoringService

_docker_client: DockerClient | None = None


def get_docker_client() -> DockerClient:
    global _docker_client
    if _docker_client is None:
        _docker_client = DockerClient()
    return _docker_client


def get_docker_service(client: DockerClient = Depends(get_docker_client)) -> DockerMonitoringService:
    return DockerMonitoringService(client)
