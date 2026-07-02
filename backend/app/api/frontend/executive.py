from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.deps import get_db
from app.integrations.aws.client import AWSCostClient
from app.integrations.aws.dependencies import get_aws_cost_client
from app.integrations.aws.exceptions import AWSError
from app.integrations.aws.schemas import CostSummary
from app.integrations.docker.dependencies import get_docker_service
from app.integrations.docker.service import DockerMonitoringService
from app.models.user import User
from app.repositories.ai_review_repository import AIReviewRepository
from app.repositories.incident_repository import IncidentRepository
from app.schemas.camel import CamelModel
from app.security.dependencies import get_current_user
from app.services.executive_service import ExecutiveMetricsService

router = APIRouter(prefix="/executive-intelligence", tags=["frontend-executive"])

_INCIDENT_ANALYTICS_MONTHS = 6
_MAX_COST_BREAKDOWN_SERVICES = 6
_TOP_COST_OPTIMIZATION_SERVICES = 3
_OPTIMIZATION_SAVINGS_RATE = 0.15  # heuristic - no CloudWatch utilization data to back a precise figure


class Trend(CamelModel):
    direction: str
    change_percent: float
    is_positive: bool


class SeriesPoint(CamelModel):
    label: str
    value: float


class HealthDimension(CamelModel):
    label: str
    score: int


class CostBreakdownItem(CamelModel):
    service: str
    monthly_cost: float
    percent_of_total: float
    trend: Trend


class CostOptimizationItem(CamelModel):
    id: str
    title: str
    description: str
    estimated_monthly_savings: float
    effort: str


class ExecutiveStats(CamelModel):
    engineering_health_score: int
    engineering_health_trend: Trend
    deployment_readiness: str
    infra_cost_monthly: float
    infra_cost_trend: Trend
    potential_monthly_savings: float
    incidents_this_quarter: int
    incidents_trend: Trend


class ExecutiveSummaryResponse(CamelModel):
    stats: ExecutiveStats
    health_trend: list[SeriesPoint]
    health_dimensions: list[HealthDimension]
    cost_breakdown: list[CostBreakdownItem]
    cost_optimizations: list[CostOptimizationItem]
    incident_analytics: list[SeriesPoint]


def get_executive_metrics_service(
    db: AsyncSession = Depends(get_db),
    docker_service: DockerMonitoringService = Depends(get_docker_service),
) -> ExecutiveMetricsService:
    return ExecutiveMetricsService(IncidentRepository(db), docker_service, AIReviewRepository(db))


def _deployment_readiness(avg_deployment_confidence: float) -> str:
    if avg_deployment_confidence >= 70:
        return "safe"
    if avg_deployment_confidence >= 40:
        return "caution"
    return "blocked"


def _last_n_months(n: int, today: date) -> list[tuple[int, int]]:
    months: list[tuple[int, int]] = []
    year, month = today.year, today.month
    for _ in range(n):
        months.append((year, month))
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    return list(reversed(months))


async def _get_cost_summary(aws_client: AWSCostClient) -> CostSummary:
    """Real AWS Cost Explorer data when credentials are available; gracefully
    degrades to zero rather than breaking the whole dashboard otherwise."""
    try:
        return await aws_client.get_monthly_cost_by_service()
    except AWSError:
        return CostSummary(total_monthly_cost=0.0, by_service=[])


@router.get("/summary", response_model=ExecutiveSummaryResponse)
async def get_summary(
    current_user: User = Depends(get_current_user),
    metrics_service: ExecutiveMetricsService = Depends(get_executive_metrics_service),
    aws_client: AWSCostClient = Depends(get_aws_cost_client),
    db: AsyncSession = Depends(get_db),
):
    breakdown = await metrics_service.compute_engineering_health_score(current_user.id)
    zero_trend = Trend(direction="flat", change_percent=0, is_positive=True)

    health_dimensions = [
        HealthDimension(label="Incident resolution rate", score=round(breakdown.incident_resolution_rate)),
        HealthDimension(label="Container health", score=round(breakdown.container_health_percent)),
        HealthDimension(label="Avg PR deployment confidence", score=round(breakdown.avg_deployment_confidence)),
    ]
    # No historical health-score snapshots are persisted yet, so this is a
    # single current data point rather than a real multi-month trend line.
    health_trend = [SeriesPoint(label=date.today().strftime("%b"), value=breakdown.overall_score)]

    cost_summary = await _get_cost_summary(aws_client)
    cost_breakdown = [
        CostBreakdownItem(
            service=service.service,
            monthly_cost=service.monthly_cost,
            percent_of_total=service.percent_of_total,
            trend=zero_trend,
        )
        for service in cost_summary.by_service[:_MAX_COST_BREAKDOWN_SERVICES]
    ]
    cost_optimizations = [
        CostOptimizationItem(
            id=f"opt-{index + 1}",
            title=f"Review {service.service} for right-sizing opportunities",
            description=(
                f"{service.service} is the #{index + 1} cost driver this month at "
                f"${service.monthly_cost:,.0f}. Estimate is a {int(_OPTIMIZATION_SAVINGS_RATE * 100)}% "
                "heuristic - connect CloudWatch utilization metrics for a precise figure."
            ),
            estimated_monthly_savings=round(service.monthly_cost * _OPTIMIZATION_SAVINGS_RATE),
            effort="medium",
        )
        for index, service in enumerate(cost_summary.by_service[:_TOP_COST_OPTIMIZATION_SERVICES])
    ]
    potential_monthly_savings = sum(item.estimated_monthly_savings for item in cost_optimizations)

    incidents = await IncidentRepository(db).list_all(limit=500)
    today = date.today()
    quarter_start_month = ((today.month - 1) // 3) * 3 + 1
    quarter_start = date(today.year, quarter_start_month, 1)
    incidents_this_quarter = sum(1 for i in incidents if i.created_at.date() >= quarter_start)

    month_buckets = _last_n_months(_INCIDENT_ANALYTICS_MONTHS, today)
    counts = {bucket: 0 for bucket in month_buckets}
    for incident in incidents:
        key = (incident.created_at.year, incident.created_at.month)
        if key in counts:
            counts[key] += 1
    incident_analytics = [
        SeriesPoint(label=date(year, month, 1).strftime("%b"), value=counts[(year, month)])
        for year, month in month_buckets
    ]

    return ExecutiveSummaryResponse(
        stats=ExecutiveStats(
            engineering_health_score=breakdown.overall_score,
            engineering_health_trend=zero_trend,
            deployment_readiness=_deployment_readiness(breakdown.avg_deployment_confidence),
            infra_cost_monthly=cost_summary.total_monthly_cost,
            infra_cost_trend=zero_trend,
            potential_monthly_savings=potential_monthly_savings,
            incidents_this_quarter=incidents_this_quarter,
            incidents_trend=zero_trend,
        ),
        health_trend=health_trend,
        health_dimensions=health_dimensions,
        cost_breakdown=cost_breakdown,
        cost_optimizations=cost_optimizations,
        incident_analytics=incident_analytics,
    )
