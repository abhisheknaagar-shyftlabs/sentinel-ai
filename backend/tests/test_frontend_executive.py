from datetime import date, datetime, timezone

from app.integrations.aws.dependencies import get_aws_cost_client
from app.integrations.aws.exceptions import AWSCredentialsError
from app.integrations.aws.schemas import CostSummary, ServiceCost
from app.integrations.docker.dependencies import get_docker_service
from app.main import app
from app.models.incident import Incident
from tests.test_github import _register_and_login

TODAY = date.today()


class FakeDockerService:
    async def list_containers(self):
        return []


class FakeAWSCostClient:
    def __init__(self, summary=None, error=None):
        self._summary = summary
        self._error = error

    async def get_monthly_cost_by_service(self):
        if self._error:
            raise self._error
        return self._summary


def _override_deps(aws_client):
    app.dependency_overrides[get_docker_service] = lambda: FakeDockerService()
    app.dependency_overrides[get_aws_cost_client] = lambda: aws_client


def _clear_overrides():
    app.dependency_overrides.pop(get_docker_service, None)
    app.dependency_overrides.pop(get_aws_cost_client, None)


async def test_executive_summary_with_real_cost_data(client):
    summary = CostSummary(
        total_monthly_cost=18240.0,
        by_service=[
            ServiceCost(service="Compute (EC2 / ECS)", monthly_cost=8640.0, percent_of_total=47.4),
            ServiceCost(service="RDS", monthly_cost=4000.0, percent_of_total=21.9),
        ],
    )
    _override_deps(FakeAWSCostClient(summary=summary))

    try:
        headers = await _register_and_login(client)
        response = await client.get("/api/executive-intelligence/summary", headers=headers)
    finally:
        _clear_overrides()

    assert response.status_code == 200
    body = response.json()

    assert body["stats"]["infraCostMonthly"] == 18240.0
    assert body["stats"]["engineeringHealthScore"] == 100
    assert body["stats"]["deploymentReadiness"] == "safe"

    assert body["costBreakdown"][0]["service"] == "Compute (EC2 / ECS)"
    assert len(body["costOptimizations"]) == 2
    assert body["costOptimizations"][0]["estimatedMonthlySavings"] == round(8640.0 * 0.15)
    assert body["stats"]["potentialMonthlySavings"] == round(8640.0 * 0.15) + round(4000.0 * 0.15)

    assert len(body["healthDimensions"]) == 3
    assert len(body["healthTrend"]) == 1
    assert len(body["incidentAnalytics"]) == 6


async def test_executive_summary_degrades_gracefully_without_aws_credentials(client):
    _override_deps(FakeAWSCostClient(error=AWSCredentialsError("no creds")))

    try:
        headers = await _register_and_login(client)
        response = await client.get("/api/executive-intelligence/summary", headers=headers)
    finally:
        _clear_overrides()

    assert response.status_code == 200
    body = response.json()
    assert body["stats"]["infraCostMonthly"] == 0
    assert body["stats"]["potentialMonthlySavings"] == 0
    assert body["costBreakdown"] == []
    assert body["costOptimizations"] == []


async def test_executive_summary_counts_incidents_this_quarter(client, db_session):
    _override_deps(FakeAWSCostClient(summary=CostSummary(total_monthly_cost=0.0, by_service=[])))

    incident = Incident(title="db outage", summary="", severity="high", status="resolved", recovery_executed=True)
    db_session.add(incident)
    await db_session.commit()

    try:
        headers = await _register_and_login(client)
        response = await client.get("/api/executive-intelligence/summary", headers=headers)
    finally:
        _clear_overrides()

    assert response.status_code == 200
    body = response.json()
    assert body["stats"]["incidentsThisQuarter"] == 1
    assert sum(point["value"] for point in body["incidentAnalytics"]) == 1


async def test_executive_summary_requires_auth(client):
    response = await client.get("/api/executive-intelligence/summary")
    assert response.status_code == 401
