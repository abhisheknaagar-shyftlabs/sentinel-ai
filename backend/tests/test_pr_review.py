from datetime import datetime, timezone

from sqlalchemy import select

from app.agents.development.schemas import (
    BreakingChangeAssessment,
    DeploymentConfidence,
    ExecutiveSummary,
    PRReviewOutput,
    Recommendation,
    RiskAssessment,
    RiskLevel,
    SuggestedFix,
    TechnicalDebt,
)
from app.continuum.client import ContinuumClient
from app.continuum.exceptions import MalformedResponseError
from app.integrations.github.client import GitHubClient
from app.integrations.github.schemas import (
    GitHubCommit,
    GitHubPullRequestDetail,
    GitHubPullRequestFile,
    GitHubRepo,
    GitHubUser,
)
from app.models.ai_fix import AIFix
from app.models.review import AIReview
from tests.test_github import _register_and_login

SAMPLE_REVIEW = PRReviewOutput(
    executive_summary=ExecutiveSummary(summary="Solid, well-tested change."),
    risk_assessment=RiskAssessment(score=20, level=RiskLevel.LOW, rationale="Narrow scope."),
    deployment_confidence=DeploymentConfidence(score=88, rationale="CI green."),
    technical_debt=TechnicalDebt(summary="None introduced."),
    breaking_changes=BreakingChangeAssessment(detected=False),
    recommendation=Recommendation.APPROVE,
    recommendation_rationale="Small, tested, no breaking changes.",
)


def _patch_github(monkeypatch):
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

    async def fake_get_pull_request(self, full_name, number):
        now = datetime.now(timezone.utc)
        return GitHubPullRequestDetail(
            number=number,
            title="Add retry logic",
            state="open",
            user_login="octocat",
            html_url=f"https://github.com/{full_name}/pull/{number}",
            created_at=now,
            updated_at=now,
            body="Adds retries to the flaky client.",
            base_branch="main",
            head_branch="feature/retries",
            additions=10,
            deletions=2,
            changed_files=1,
        )

    async def fake_get_pull_request_diff(self, full_name, number):
        return "diff --git a/x.py b/x.py\n+retry()\n"

    async def fake_list_pull_request_files(self, full_name, number):
        return [GitHubPullRequestFile(filename="x.py", status="modified", additions=10, deletions=2, changes=12)]

    async def fake_list_pull_request_commits(self, full_name, number):
        return [GitHubCommit(sha="abc1234", message="add retries", html_url="https://github.com/x")]

    monkeypatch.setattr(GitHubClient, "get_authenticated_user", fake_get_authenticated_user)
    monkeypatch.setattr(GitHubClient, "get_repository", fake_get_repository)
    monkeypatch.setattr(GitHubClient, "get_pull_request", fake_get_pull_request)
    monkeypatch.setattr(GitHubClient, "get_pull_request_diff", fake_get_pull_request_diff)
    monkeypatch.setattr(GitHubClient, "list_pull_request_files", fake_list_pull_request_files)
    monkeypatch.setattr(GitHubClient, "list_pull_request_commits", fake_list_pull_request_commits)


async def _connect_and_track(client, headers) -> str:
    integration_response = await client.post(
        "/api/v1/github/integrations", json={"personal_access_token": "ghp_fake"}, headers=headers
    )
    integration_id = integration_response.json()["data"]["id"]

    track_response = await client.post(
        f"/api/v1/github/integrations/{integration_id}/repositories",
        json={"full_name": "octocat/sentinel-ai"},
        headers=headers,
    )
    return track_response.json()["data"]["id"]


async def test_review_pull_request_persists_and_returns_structured_result(client, db_session, monkeypatch):
    _patch_github(monkeypatch)

    async def fake_run_prompt(self, **kwargs):
        assert kwargs["output_schema"] is PRReviewOutput
        return SAMPLE_REVIEW

    monkeypatch.setattr(ContinuumClient, "run_prompt", fake_run_prompt)

    headers = await _register_and_login(client)
    repository_id = await _connect_and_track(client, headers)

    response = await client.post(
        f"/api/v1/github/repositories/{repository_id}/pulls/7/review", headers=headers
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["recommendation"] == "approve"
    assert data["risk_assessment"]["score"] == 20

    rows = (await db_session.execute(select(AIReview))).scalars().all()
    assert len(rows) == 1
    assert rows[0].pull_request_number == 7
    assert rows[0].risk_score == 20
    assert rows[0].recommendation == "approve"


async def test_review_persists_suggested_fixes(client, db_session, monkeypatch):
    _patch_github(monkeypatch)

    review_with_fix = SAMPLE_REVIEW.model_copy(
        update={
            "code_fix_suggestions": [
                SuggestedFix(
                    file="x.py",
                    description="Add exponential backoff to the retry loop.",
                    suggested_patch="+ time.sleep(2 ** attempt)",
                    confidence=91,
                )
            ]
        }
    )

    async def fake_run_prompt(self, **kwargs):
        return review_with_fix

    monkeypatch.setattr(ContinuumClient, "run_prompt", fake_run_prompt)

    headers = await _register_and_login(client)
    repository_id = await _connect_and_track(client, headers)

    response = await client.post(
        f"/api/v1/github/repositories/{repository_id}/pulls/7/review", headers=headers
    )
    assert response.status_code == 200

    fixes = (await db_session.execute(select(AIFix))).scalars().all()
    assert len(fixes) == 1
    assert fixes[0].file == "x.py"
    assert fixes[0].confidence == 91
    assert fixes[0].status == "suggested"


async def test_review_unowned_repository_returns_404(client, monkeypatch):
    _patch_github(monkeypatch)
    headers = await _register_and_login(client)

    response = await client.post(
        "/api/v1/github/repositories/00000000-0000-0000-0000-000000000000/pulls/1/review",
        headers=headers,
    )
    assert response.status_code == 404


async def test_malformed_ai_response_maps_to_422(client, monkeypatch):
    _patch_github(monkeypatch)

    async def fake_run_prompt(self, **kwargs):
        raise MalformedResponseError("could not parse JSON")

    monkeypatch.setattr(ContinuumClient, "run_prompt", fake_run_prompt)

    headers = await _register_and_login(client)
    repository_id = await _connect_and_track(client, headers)

    response = await client.post(
        f"/api/v1/github/repositories/{repository_id}/pulls/7/review", headers=headers
    )
    assert response.status_code == 422
    assert response.json()["success"] is False


async def test_unauthenticated_review_request_rejected(client):
    response = await client.post(
        "/api/v1/github/repositories/00000000-0000-0000-0000-000000000000/pulls/1/review"
    )
    assert response.status_code == 401
