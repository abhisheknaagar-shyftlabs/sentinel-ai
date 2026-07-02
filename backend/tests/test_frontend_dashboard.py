import uuid
from datetime import datetime, timezone

from app.integrations.aws.dependencies import get_aws_cost_client
from app.integrations.aws.schemas import CostSummary
from app.integrations.docker.dependencies import get_docker_service
from app.integrations.docker.schemas import ContainerHealthStatus, ContainerSummary
from app.integrations.github.client import GitHubClient
from app.integrations.github.schemas import GitHubPullRequestSummary
from app.main import app
from app.models.incident import Incident, IncidentEvent
from app.models.review import AIReview
from tests.test_frontend_development import _connect_and_track, _patch_github_base
from tests.test_github import _register_and_login

NOW = datetime.now(timezone.utc)


class FakeDockerService:
    def __init__(self, containers=None):
        self._containers = containers or []

    async def list_containers(self):
        return self._containers


class FakeAWSCostClient:
    async def get_monthly_cost_by_service(self):
        return CostSummary(total_monthly_cost=0.0, by_service=[])


def _make_container(container_id, health, running=True):
    return ContainerSummary(
        id=container_id,
        short_id=container_id[:12],
        name=f"svc-{container_id}",
        image="app:latest",
        status="running" if running else "exited",
        health=health,
        running=running,
        created_at=NOW,
        started_at=NOW,
        restart_count=0,
    )


def _override(containers=None):
    app.dependency_overrides[get_docker_service] = lambda: FakeDockerService(containers)
    app.dependency_overrides[get_aws_cost_client] = lambda: FakeAWSCostClient()


def _clear():
    app.dependency_overrides.pop(get_docker_service, None)
    app.dependency_overrides.pop(get_aws_cost_client, None)


async def test_dashboard_with_no_data_returns_healthy_defaults(client):
    _override()
    try:
        headers = await _register_and_login(client)
        response = await client.get("/api/dashboard/summary", headers=headers)
    finally:
        _clear()

    assert response.status_code == 200
    body = response.json()
    assert body["stats"]["openPRsAtRisk"] == 0
    assert body["stats"]["containersHealthy"] == 0
    assert body["stats"]["containersTotal"] == 0
    assert body["stats"]["openIncidents"] == 0
    assert body["stats"]["engineeringHealthScore"] == 100
    assert body["developmentSnapshot"]["headline"] == "No open pull requests"
    assert body["productionSnapshot"]["headline"] == "All systems healthy"
    assert body["executiveSnapshot"]["headline"] == "Engineering health at 100/100"
    assert body["healthTrend"][0]["value"] == 100


async def test_dashboard_flags_at_risk_pr_from_cached_review(client, db_session, monkeypatch):
    _patch_github_base(monkeypatch)
    _override()

    async def fake_list_pull_requests(self, full_name, state="open"):
        return [
            GitHubPullRequestSummary(
                number=482,
                title="Refactor payment retry logic",
                state="open",
                user_login="a.torres",
                html_url="https://github.com/x/pull/482",
                created_at=NOW,
                updated_at=NOW,
                draft=False,
                base_branch="main",
                head_branch="feat/payment-retry",
            )
        ]

    monkeypatch.setattr(GitHubClient, "list_pull_requests", fake_list_pull_requests)

    try:
        headers = await _register_and_login(client)
        repo_id = await _connect_and_track(client, headers)

        review = AIReview(
            repository_id=uuid.UUID(repo_id),
            pull_request_number=482,
            summary="Rewrites retry logic.",
            risk_score=80,
            deployment_confidence=55,
            recommendation="approve_with_changes",
            technical_debt_summary="No backoff yet.",
        )
        db_session.add(review)
        await db_session.commit()

        response = await client.get("/api/dashboard/summary", headers=headers)
    finally:
        _clear()

    assert response.status_code == 200
    body = response.json()
    assert body["stats"]["openPRsAtRisk"] == 1
    assert body["developmentSnapshot"]["risk"] == "high"


async def test_dashboard_shows_open_incident_and_unhealthy_container(client, db_session):
    _override(containers=[_make_container("aaa", ContainerHealthStatus.UNHEALTHY)])

    incident = Incident(title="notifications service degraded", summary="", severity="high", status="open")
    incident.events.append(IncidentEvent(event_type="incident_created", message="Incident created"))
    db_session.add(incident)
    await db_session.commit()

    try:
        headers = await _register_and_login(client)
        response = await client.get("/api/dashboard/summary", headers=headers)
    finally:
        _clear()

    assert response.status_code == 200
    body = response.json()
    assert body["stats"]["openIncidents"] == 1
    assert body["stats"]["containersHealthy"] == 0
    assert body["stats"]["containersTotal"] == 1
    assert body["productionSnapshot"]["headline"] == "notifications service degraded"
    assert body["productionSnapshot"]["health"] == "unhealthy"
    assert any(item["title"] == "Incident created" for item in body["recentActivity"])


async def test_dashboard_requires_auth(client):
    response = await client.get("/api/dashboard/summary")
    assert response.status_code == 401
