import uuid

from app.agents.development.schemas import RiskLevel
from app.integrations.github.client import GitHubClient
from app.integrations.github.schemas import GitHubRepo, GitHubUser
from app.models.review import AIReview
from app.repositories.ai_review_repository import AIReviewRepository
from app.repositories.tracked_repository_repository import TrackedRepositoryRepository
from app.services.technical_debt_service import TechnicalDebtService
from app.utils.time import utc_now
from tests.test_github import _register_and_login


async def _register_and_track_repo(client, monkeypatch) -> tuple[dict, str]:
    async def fake_get_authenticated_user(self):
        return GitHubUser(login="octocat", id=1, type="User"), ["repo"]

    async def fake_get_repository(self, full_name):
        return GitHubRepo(
            id=999,
            name="sentinel-ai",
            full_name=full_name,
            private=False,
            default_branch="main",
            html_url=f"https://github.com/{full_name}",
            description=None,
        )

    monkeypatch.setattr(GitHubClient, "get_authenticated_user", fake_get_authenticated_user)
    monkeypatch.setattr(GitHubClient, "get_repository", fake_get_repository)

    headers = await _register_and_login(client)
    integration_response = await client.post(
        "/api/v1/github/integrations", json={"personal_access_token": "ghp_fake"}, headers=headers
    )
    integration_id = integration_response.json()["data"]["id"]
    track_response = await client.post(
        f"/api/v1/github/integrations/{integration_id}/repositories",
        json={"full_name": "octocat/sentinel-ai"},
        headers=headers,
    )
    return headers, track_response.json()["data"]["id"]


async def test_list_technical_debt_skips_trivial_summaries(client, db_session, monkeypatch):
    headers, repository_id = await _register_and_track_repo(client, monkeypatch)
    repository_uuid = uuid.UUID(repository_id)

    reviews = AIReviewRepository(db_session)
    me_response = await client.get("/api/v1/auth/me", headers=headers)
    user_id = me_response.json()["data"]["id"]

    await reviews.create(
        AIReview(
            repository_id=repository_uuid,
            pull_request_number=1,
            review_timestamp=utc_now(),
            summary="Trivial change.",
            risk_score=10,
            deployment_confidence=95,
            recommendation="approve",
            technical_debt_summary="None introduced.",
        )
    )
    await reviews.create(
        AIReview(
            repository_id=repository_uuid,
            pull_request_number=2,
            review_timestamp=utc_now(),
            summary="Adds a workaround.",
            risk_score=70,
            deployment_confidence=60,
            recommendation="approve_with_changes",
            technical_debt_summary="Uses a deprecated v1 template engine for PDF generation.",
        )
    )

    service = TechnicalDebtService(reviews, TrackedRepositoryRepository(db_session))
    items = await service.list_technical_debt(uuid.UUID(user_id))

    assert len(items) == 1
    assert items[0].description == "Uses a deprecated v1 template engine for PDF generation."
    assert items[0].severity == RiskLevel.HIGH
    assert items[0].module == "octocat/sentinel-ai"
