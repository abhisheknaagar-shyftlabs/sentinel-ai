from fastapi import APIRouter, Depends
from pydantic import Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.frontend.development import _risk_level_from_score, get_github_service
from app.api.frontend.executive import _get_cost_summary, get_executive_metrics_service
from app.api.frontend.production import _map_container_status
from app.database.deps import get_db
from app.integrations.aws.client import AWSCostClient
from app.integrations.aws.dependencies import get_aws_cost_client
from app.integrations.docker.dependencies import get_docker_service
from app.integrations.docker.service import DockerMonitoringService
from app.models.user import User
from app.repositories.ai_fix_repository import AIFixRepository
from app.repositories.ai_review_repository import AIReviewRepository
from app.repositories.incident_repository import IncidentRepository
from app.schemas.camel import CamelModel
from app.schemas.incident import IncidentStatus
from app.security.dependencies import get_current_user
from app.services.executive_service import ExecutiveMetricsService
from app.services.github_service import GitHubIntegrationService
from app.utils.time import format_relative_time, utc_now

router = APIRouter(prefix="/dashboard", tags=["frontend-dashboard"])

_MAX_RECENT_ACTIVITY = 10
_RISK_RANK = {"low": 0, "medium": 1, "high": 2, "critical": 3}
_EVENT_TONE = {
    "incident_created": "warning",
    "analysis_started": "neutral",
    "analysis_completed": "neutral",
    "analysis_failed": "danger",
    "recovery_started": "warning",
    "recovery_completed": "success",
    "recovery_failed": "danger",
    "resolved": "success",
}


class Trend(CamelModel):
    direction: str
    change_percent: float
    is_positive: bool


class DashboardStats(CamelModel):
    open_prs_at_risk: int = Field(serialization_alias="openPRsAtRisk")
    open_prs_at_risk_trend: Trend = Field(serialization_alias="openPRsAtRiskTrend")
    containers_healthy: int
    containers_total: int
    open_incidents: int
    open_incidents_trend: Trend
    engineering_health_score: int
    engineering_health_trend: Trend
    infra_cost_monthly: float
    infra_cost_trend: Trend
    deployment_confidence_percent: int
    deployment_confidence_trend: Trend


class DevelopmentSnapshot(CamelModel):
    headline: str
    detail: str
    risk: str


class ProductionSnapshot(CamelModel):
    headline: str
    detail: str
    health: str


class ExecutiveSnapshot(CamelModel):
    headline: str
    detail: str
    trend: Trend


class SeriesPoint(CamelModel):
    label: str
    value: float


class TimelineItem(CamelModel):
    id: str
    title: str
    description: str | None = None
    timestamp: str
    tone: str


class DashboardSummaryResponse(CamelModel):
    stats: DashboardStats
    development_snapshot: DevelopmentSnapshot
    production_snapshot: ProductionSnapshot
    executive_snapshot: ExecutiveSnapshot
    health_trend: list[SeriesPoint]
    recent_activity: list[TimelineItem]


def get_dashboard_services(
    db: AsyncSession = Depends(get_db),
    docker_service: DockerMonitoringService = Depends(get_docker_service),
    metrics_service: ExecutiveMetricsService = Depends(get_executive_metrics_service),
    github_service: GitHubIntegrationService = Depends(get_github_service),
    aws_client: AWSCostClient = Depends(get_aws_cost_client),
):
    return {
        "db": db,
        "docker_service": docker_service,
        "metrics_service": metrics_service,
        "github_service": github_service,
        "aws_client": aws_client,
    }


@router.get("/summary", response_model=DashboardSummaryResponse)
async def get_summary(
    current_user: User = Depends(get_current_user),
    services: dict = Depends(get_dashboard_services),
):
    db = services["db"]
    docker_service = services["docker_service"]
    github_service = services["github_service"]

    zero_trend = Trend(direction="flat", change_percent=0, is_positive=True)

    # --- development: at-risk open PRs, from cached reviews only - the
    # dashboard is a landing page, so it never triggers a fresh AI review. ---
    tracked_repos = await github_service.list_tracked_repositories(current_user.id)
    open_pr_keys: set[tuple] = set()
    for repo in tracked_repos:
        prs = await github_service.list_pull_requests(current_user.id, repo.id, state="open")
        open_pr_keys.update((repo.id, pr.number) for pr in prs)

    ai_reviews = AIReviewRepository(db)
    recent_reviews = await ai_reviews.list_recent_for_user(current_user.id, limit=200)
    latest_review_by_pr: dict[tuple, object] = {}
    for review in recent_reviews:
        key = (review.repository_id, review.pull_request_number)
        if key not in latest_review_by_pr:  # already ordered newest-first
            latest_review_by_pr[key] = review

    open_pr_risks = [
        _risk_level_from_score(latest_review_by_pr[key].risk_score)
        for key in open_pr_keys
        if key in latest_review_by_pr
    ]
    open_prs_at_risk = sum(1 for risk in open_pr_risks if risk in ("high", "critical"))

    if not open_pr_keys:
        development_snapshot = DevelopmentSnapshot(
            headline="No open pull requests", detail="Nothing pending review right now.", risk="low"
        )
    else:
        worst_risk = max(open_pr_risks, key=lambda r: _RISK_RANK[r]) if open_pr_risks else "low"
        development_snapshot = DevelopmentSnapshot(
            headline=f"{len(open_pr_keys)} pull request(s) need review",
            detail=(
                f"{open_prs_at_risk} high-risk PR(s) flagged before merge."
                if open_prs_at_risk
                else "No high-risk PRs detected in the latest reviews."
            ),
            risk=worst_risk,
        )

    # --- production: containers + incidents ---
    containers = await docker_service.list_containers()
    container_statuses = [_map_container_status(c) for c in containers]
    containers_healthy = sum(1 for status in container_statuses if status == "healthy")
    containers_total = len(container_statuses)

    incidents = await IncidentRepository(db).list_all(limit=200)
    open_incidents_list = [i for i in incidents if i.status != IncidentStatus.RESOLVED.value]
    open_incidents = len(open_incidents_list)

    if "unhealthy" in container_statuses:
        overall_health = "unhealthy"
    elif "degraded" in container_statuses:
        overall_health = "degraded"
    elif "unknown" in container_statuses:
        overall_health = "unknown"
    else:
        overall_health = "healthy"

    if open_incidents_list:
        primary_incident = open_incidents_list[0]
        production_snapshot = ProductionSnapshot(
            headline=primary_incident.title,
            detail=primary_incident.root_cause_summary or "Investigation in progress.",
            health=overall_health,
        )
    else:
        production_snapshot = ProductionSnapshot(
            headline="All systems healthy",
            detail=f"{containers_healthy}/{containers_total} containers healthy, no open incidents.",
            health=overall_health,
        )

    # --- executive: health score + cost ---
    breakdown = await services["metrics_service"].compute_engineering_health_score(current_user.id)
    cost_summary = await _get_cost_summary(services["aws_client"])

    executive_snapshot = ExecutiveSnapshot(
        headline=f"Engineering health at {breakdown.overall_score}/100",
        detail=(
            f"Incident resolution {round(breakdown.incident_resolution_rate)}%, "
            f"container health {round(breakdown.container_health_percent)}%, "
            f"deployment confidence {round(breakdown.avg_deployment_confidence)}%."
        ),
        trend=zero_trend,
    )

    # No historical daily snapshots are persisted yet, so this is a single
    # current data point rather than a real 7-day trend line.
    health_trend = [SeriesPoint(label=utc_now().strftime("%a"), value=breakdown.overall_score)]

    # --- recent activity: real AI fixes + real incident timeline events ---
    ai_fixes = await AIFixRepository(db).list_recent_for_user(current_user.id, limit=10)
    activity: list[tuple] = [
        (
            fix.created_at,
            TimelineItem(
                id=f"fix-{fix.id}",
                title=f"AI generated a fix for PR #{fix.pull_request_number}",
                description=fix.description,
                timestamp=format_relative_time(fix.created_at),
                tone="success",
            ),
        )
        for fix in ai_fixes
    ]
    for incident in incidents:
        for event in incident.events[-3:]:
            activity.append(
                (
                    event.created_at,
                    TimelineItem(
                        id=f"event-{event.id}",
                        title=event.message,
                        description=incident.title,
                        timestamp=format_relative_time(event.created_at),
                        tone=_EVENT_TONE.get(event.event_type, "neutral"),
                    ),
                )
            )

    activity.sort(key=lambda pair: pair[0], reverse=True)
    recent_activity = [item for _, item in activity[:_MAX_RECENT_ACTIVITY]]

    return DashboardSummaryResponse(
        stats=DashboardStats(
            open_prs_at_risk=open_prs_at_risk,
            open_prs_at_risk_trend=zero_trend,
            containers_healthy=containers_healthy,
            containers_total=containers_total,
            open_incidents=open_incidents,
            open_incidents_trend=zero_trend,
            engineering_health_score=breakdown.overall_score,
            engineering_health_trend=zero_trend,
            infra_cost_monthly=cost_summary.total_monthly_cost,
            infra_cost_trend=zero_trend,
            deployment_confidence_percent=round(breakdown.avg_deployment_confidence),
            deployment_confidence_trend=zero_trend,
        ),
        development_snapshot=development_snapshot,
        production_snapshot=production_snapshot,
        executive_snapshot=executive_snapshot,
        health_trend=health_trend,
        recent_activity=recent_activity,
    )
