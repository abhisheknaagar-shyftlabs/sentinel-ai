import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.continuum.client import ContinuumClient
from app.continuum.dependencies import get_continuum_client
from app.core.responses import success_envelope
from app.database.deps import get_db
from app.integrations.docker.dependencies import get_docker_service
from app.integrations.docker.service import DockerMonitoringService
from app.integrations.slack.client import SlackClient
from app.integrations.slack.dependencies import get_slack_client
from app.models.user import User
from app.repositories.incident_repository import IncidentRepository
from app.schemas.incident import IncidentCreateRequest, IncidentRead
from app.security.dependencies import get_current_user
from app.services.incident_service import IncidentService
from app.services.root_cause_service import RootCauseAnalysisService

router = APIRouter(prefix="/incidents", tags=["incidents"])


def get_incident_service(
    db: AsyncSession = Depends(get_db),
    docker_service: DockerMonitoringService = Depends(get_docker_service),
    continuum_client: ContinuumClient = Depends(get_continuum_client),
    slack_client: SlackClient = Depends(get_slack_client),
) -> IncidentService:
    root_cause_service = RootCauseAnalysisService(docker_service, continuum_client)
    return IncidentService(IncidentRepository(db), docker_service, root_cause_service, slack_client)


@router.get("", summary="List all incidents")
async def list_incidents(
    current_user: User = Depends(get_current_user),
    service: IncidentService = Depends(get_incident_service),
):
    incidents = await service.list_incidents()
    return success_envelope([IncidentRead.model_validate(i).model_dump(mode="json") for i in incidents])


@router.get("/{incident_id}", summary="Get one incident, including its timeline")
async def get_incident(
    incident_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: IncidentService = Depends(get_incident_service),
):
    incident = await service.get_incident(incident_id)
    return success_envelope(IncidentRead.model_validate(incident).model_dump(mode="json"))


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Open a new incident",
    description="Collects live Docker metadata for each affected container and stores it as evidence.",
)
async def create_incident(
    payload: IncidentCreateRequest,
    current_user: User = Depends(get_current_user),
    service: IncidentService = Depends(get_incident_service),
):
    incident = await service.create_incident(payload)
    return success_envelope(IncidentRead.model_validate(incident).model_dump(mode="json"), "Incident created")


@router.post(
    "/{incident_id}/analyze",
    summary="Run root cause analysis on an incident",
    description=(
        "Reuses the existing Root Cause Analysis agent against the incident's primary affected "
        "container - no AI logic is duplicated here. Moves the incident to recovery_available if "
        "the analysis judges an automatic restart safe, otherwise to analyzed."
    ),
)
async def analyze_incident(
    incident_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: IncidentService = Depends(get_incident_service),
):
    incident = await service.analyze_incident(incident_id)
    return success_envelope(
        IncidentRead.model_validate(incident).model_dump(mode="json"), "Incident analysis completed"
    )


@router.post(
    "/{incident_id}/recover",
    summary="Execute recovery for an incident",
    description=(
        "Only valid once an incident is in recovery_available status. Reuses the existing safe "
        "restart implementation from Docker Monitoring - no restart logic is duplicated here."
    ),
)
async def recover_incident(
    incident_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: IncidentService = Depends(get_incident_service),
):
    incident = await service.recover_incident(incident_id)
    return success_envelope(
        IncidentRead.model_validate(incident).model_dump(mode="json"), "Incident recovery completed"
    )
