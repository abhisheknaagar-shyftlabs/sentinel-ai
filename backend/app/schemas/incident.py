import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from app.agents.production.schemas import Severity

__all__ = ["Severity"]  # re-exported so callers don't need to know it lives under agents/production


class IncidentStatus(str, Enum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    ANALYZED = "analyzed"
    RECOVERY_AVAILABLE = "recovery_available"
    RESOLVED = "resolved"


class IncidentEventType(str, Enum):
    INCIDENT_CREATED = "incident_created"
    ANALYSIS_STARTED = "analysis_started"
    ANALYSIS_COMPLETED = "analysis_completed"
    ANALYSIS_FAILED = "analysis_failed"
    RECOVERY_STARTED = "recovery_started"
    RECOVERY_COMPLETED = "recovery_completed"
    RECOVERY_FAILED = "recovery_failed"
    RESOLVED = "resolved"


class IncidentCreateRequest(BaseModel):
    title: str = Field(min_length=1)
    summary: str | None = None
    severity: Severity = Severity.MEDIUM
    container_ids: list[str] = Field(
        default_factory=list, description="Docker container IDs or names affected by this incident"
    )


class AffectedContainerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    container_id: str
    container_name: str
    image: str


class IncidentEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    event_type: str
    message: str
    created_at: datetime


class IncidentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    summary: str
    severity: Severity
    status: IncidentStatus
    created_at: datetime
    resolved_at: datetime | None
    affected_containers: list[AffectedContainerRead]
    root_cause_summary: str | None
    root_cause_confidence: int | None
    recovery_recommendation: str | None
    recovery_executed: bool
    recovery_result: str | None
    events: list[IncidentEventRead]
