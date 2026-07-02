from enum import Enum

from pydantic import BaseModel, Field

from app.integrations.docker.schemas import ContainerDetail, ContainerLogs


class RootCauseAnalysisInput(BaseModel):
    """Reuses Docker Monitoring's own schemas directly - the agent never
    talks to Docker itself, it only ever sees what DockerMonitoringService
    already collected."""

    container: ContainerDetail
    logs: ContainerLogs


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ConfidenceScore(BaseModel):
    score: int = Field(ge=0, le=100)
    rationale: str


class Evidence(BaseModel):
    source: str = Field(description="Where this evidence came from, e.g. 'logs', 'stats', 'metadata'")
    description: str


class RootCause(BaseModel):
    summary: str
    category: str = Field(
        description="e.g. resource_exhaustion, configuration_error, dependency_failure, code_defect, external, unknown"
    )
    evidence: list[Evidence] = Field(default_factory=list)
    confidence: ConfidenceScore


class IncidentSummary(BaseModel):
    container_id: str
    container_name: str
    observed_state: str
    summary: str
    severity: Severity
    business_impact: str


class Recommendation(BaseModel):
    action: str
    rationale: str


class RecoveryPlan(BaseModel):
    """Diagnosis only - this phase never restarts anything. Shaped so the
    future Safe Recovery phase can consume it directly without redesign."""

    recommended_actions: list[Recommendation] = Field(default_factory=list)
    auto_restart_safe: bool
    auto_restart_rationale: str
    requires_human_intervention: bool
    human_intervention_reason: str | None = None
    long_term_fix: str | None = None


class RootCauseAnalysisResponse(BaseModel):
    incident_summary: IncidentSummary
    root_cause: RootCause
    recovery_plan: RecoveryPlan


class IncidentDiagnosis(BaseModel):
    """Deliberately smaller alternative to RootCauseAnalysisResponse - 3
    nested objects (incident_summary/root_cause/recovery_plan) with list
    fields (evidence, recommended_actions as objects) is exactly the shape
    CLAUDE.md's Continuum gotchas document as reliably hitting the Smart
    Gateway's ~180s reverse-proxy ceiling, empirically confirmed live against
    this very agent. Used only by the health monitor's automatic incident
    path (app/services/health_monitor.py via IncidentService.analyze_incident);
    the original root_cause agent/RootCauseAnalysisResponse, used by the
    on-demand POST /docker/containers/{id}/analyze endpoint, is untouched."""

    summary: str
    severity: Severity
    confidence: int = Field(ge=0, le=100)
    recommended_actions: list[str] = Field(default_factory=list)
    auto_restart_safe: bool
    auto_restart_rationale: str
    requires_human_intervention: bool
    human_intervention_reason: str | None = None
