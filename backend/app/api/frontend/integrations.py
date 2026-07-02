from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.frontend.development import get_github_service
from app.core.exceptions import AppException, ValidationAppError
from app.core.logging import get_logger
from app.database.deps import get_db
from app.integrations.docker.dependencies import get_docker_service
from app.integrations.docker.service import DockerMonitoringService
from app.models.user import User
from app.repositories.integration_repository import IntegrationRepository
from app.schemas.camel import CamelModel
from app.schemas.integration import IntegrationCreate
from app.schemas.repository import RepositoryTrackRequest
from app.security.dependencies import get_current_user
from app.services.github_service import GitHubIntegrationService
from app.utils.time import format_relative_time

router = APIRouter(prefix="/integrations", tags=["frontend-integrations"])
logger = get_logger(__name__)


class IntegrationStatus(CamelModel):
    id: str
    name: str
    description: str
    category: str
    status: str
    connected_account: str | None = None
    last_synced_at: str | None = None
    # Only ever populated by the connect endpoint below, when a repository
    # was requested alongside the token - absent from the plain list response.
    repository_tracked: str | None = None
    repository_error: str | None = None


class ConnectIntegrationRequest(CamelModel):
    personal_access_token: str | None = None
    repository_full_name: str | None = None


async def _github_status(db: AsyncSession, user_id) -> IntegrationStatus:
    github_integrations = await IntegrationRepository(db).list_for_user(user_id)
    connection = next((i for i in github_integrations if i.is_active), None)
    return IntegrationStatus(
        id="github",
        name="GitHub",
        description="Pull request reviews, risk analysis, and repository insights.",
        category="source-control",
        status="connected" if connection else "disconnected",
        connected_account=connection.account_login if connection else None,
        last_synced_at=(format_relative_time(connection.last_validated_at) if connection else None),
    )


async def _docker_status(docker_service: DockerMonitoringService) -> IntegrationStatus:
    try:
        docker_ok = await docker_service.health()
    except Exception:  # noqa: BLE001 - any failure to reach the daemon means "disconnected"
        docker_ok = False
    return IntegrationStatus(
        id="docker",
        name="Docker",
        description="Container health, live metrics, and log streaming.",
        category="containers",
        status="connected" if docker_ok else "disconnected",
    )


@router.get("", response_model=list[IntegrationStatus])
async def list_integrations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    docker_service: DockerMonitoringService = Depends(get_docker_service),
):
    """GitHub and Docker are real. Prometheus/Grafana are deliberately
    omitted rather than shown as a fake status - neither exists in this
    backend yet."""
    return [await _github_status(db, current_user.id), await _docker_status(docker_service)]


@router.post("/{integration_id}/connect", response_model=IntegrationStatus)
async def connect_integration(
    integration_id: str,
    payload: ConnectIntegrationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    github_service: GitHubIntegrationService = Depends(get_github_service),
):
    """Only GitHub supports a real manual connect - it's the only
    integration backed by a stored credential. Docker is monitored live off
    the local daemon, so there's nothing for a user to "connect"."""
    if integration_id != "github":
        raise ValidationAppError(f"'{integration_id}' does not support manual connect")
    if not payload.personal_access_token:
        raise ValidationAppError("personalAccessToken is required to connect GitHub")

    integration = await github_service.connect_integration(
        current_user.id, IntegrationCreate(personal_access_token=payload.personal_access_token)
    )

    status_result = await _github_status(db, current_user.id)
    if payload.repository_full_name:
        try:
            await github_service.track_repository(
                current_user.id, integration.id, RepositoryTrackRequest(full_name=payload.repository_full_name)
            )
            status_result.repository_tracked = payload.repository_full_name
        except AppException as exc:
            # The connect itself already succeeded and persisted - a bad repo
            # name shouldn't roll that back or mask the connect success.
            logger.warning(
                "github_connect_repo_tracking_failed",
                extra={"repository_full_name": payload.repository_full_name, "error": str(exc)},
            )
            status_result.repository_error = str(exc)
    return status_result


@router.post("/{integration_id}/disconnect", response_model=IntegrationStatus)
async def disconnect_integration(
    integration_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    github_service: GitHubIntegrationService = Depends(get_github_service),
):
    if integration_id != "github":
        raise ValidationAppError(f"'{integration_id}' does not support manual disconnect")

    github_integrations = await IntegrationRepository(db).list_for_user(current_user.id)
    connection = next((i for i in github_integrations if i.is_active), None)
    if connection is not None:
        await github_service.disconnect_integration(current_user.id, connection.id)
    return await _github_status(db, current_user.id)
