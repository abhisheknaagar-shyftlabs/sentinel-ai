import asyncio
from datetime import datetime, timedelta, timezone

from app.agents.development.schemas import (
    BreakingChangeAssessment,
    CompareReviewOutput,
    DeploymentConfidence,
    ExecutiveSummary,
    Finding,
    PRReviewOutput,
    Recommendation,
    RiskAssessment,
    RiskLevel,
    TechnicalDebt,
)
from app.continuum.client import ContinuumClient
from app.integrations.github.client import GitHubClient
from app.integrations.github.schemas import (
    GitHubBranch,
    GitHubComparison,
    GitHubComparisonFile,
    GitHubPullRequestFile,
    GitHubPullRequestSummary,
    GitHubRepo,
    GitHubUser,
)
from tests.test_github import _register_and_login

NOW = datetime.now(timezone.utc)


def _patch_github_base(monkeypatch):
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


async def test_dev_summary_never_runs_a_review_automatically(client, monkeypatch):
    _patch_github_base(monkeypatch)

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

    async def fake_list_pull_request_files(self, full_name, number):
        return [
            GitHubPullRequestFile(filename="a.py", status="modified", additions=200, deletions=100, changes=300)
        ]

    call_count = {"n": 0}

    async def fake_run_prompt(self, **kwargs):
        call_count["n"] += 1
        raise AssertionError("get_summary must never trigger a real review")

    monkeypatch.setattr(GitHubClient, "list_pull_requests", fake_list_pull_requests)
    monkeypatch.setattr(GitHubClient, "list_pull_request_files", fake_list_pull_request_files)
    monkeypatch.setattr(ContinuumClient, "run_prompt", fake_run_prompt)

    headers = await _register_and_login(client)
    await _connect_and_track(client, headers)

    response = await client.get("/api/development-intelligence/summary", headers=headers)
    assert response.status_code == 200
    body = response.json()

    assert call_count["n"] == 0
    assert body["stats"]["openPRs"] == 1
    assert body["stats"]["highRiskPRs"] == 0

    pr = body["pullRequests"][0]
    assert pr["number"] == 482
    assert pr["reviewed"] is False
    assert pr["linesAdded"] == 200
    assert "repositoryId" in pr

    assert body["technicalDebt"] == []
    assert body["aiFixes"] == []


async def test_dev_summary_shows_cached_review_without_running_a_fresh_one(client, db_session, monkeypatch):
    import uuid

    from app.models.review import AIReview

    _patch_github_base(monkeypatch)

    older = NOW - timedelta(hours=2)

    async def fake_list_pull_requests(self, full_name, state="open"):
        return [
            GitHubPullRequestSummary(
                number=100,
                title="Older PR - already reviewed earlier",
                state="open",
                user_login="a.torres",
                html_url="https://github.com/x/pull/100",
                created_at=older,
                updated_at=older,
                draft=False,
                base_branch="main",
                head_branch="feat/old-pr",
            ),
            GitHubPullRequestSummary(
                number=200,
                title="Newer PR - never reviewed",
                state="open",
                user_login="b.lee",
                html_url="https://github.com/x/pull/200",
                created_at=NOW,
                updated_at=NOW,
                draft=False,
                base_branch="main",
                head_branch="feat/new-pr",
            ),
        ]

    async def fake_list_pull_request_files(self, full_name, number):
        return []

    call_count = {"n": 0}

    async def fake_run_prompt(self, **kwargs):
        call_count["n"] += 1
        raise AssertionError("get_summary must never trigger a real review, cached or not")

    monkeypatch.setattr(GitHubClient, "list_pull_requests", fake_list_pull_requests)
    monkeypatch.setattr(GitHubClient, "list_pull_request_files", fake_list_pull_request_files)
    monkeypatch.setattr(ContinuumClient, "run_prompt", fake_run_prompt)

    headers = await _register_and_login(client)
    repo_id = await _connect_and_track(client, headers)

    # Simulate PR #100 having already been reviewed earlier via the
    # on-demand endpoint - get_summary should surface this from cache.
    db_session.add(
        AIReview(
            repository_id=uuid.UUID(repo_id),
            pull_request_number=100,
            summary="Trivial change.",
            risk_score=20,
            deployment_confidence=95,
            recommendation="approve",
            technical_debt_summary="None.",
        )
    )
    await db_session.commit()

    response = await client.get("/api/development-intelligence/summary", headers=headers)
    assert response.status_code == 200
    body = response.json()

    assert call_count["n"] == 0

    prs_by_number = {pr["number"]: pr for pr in body["pullRequests"]}
    assert prs_by_number[100]["reviewed"] is True
    assert prs_by_number[100]["deploymentConfidence"] == 95
    assert prs_by_number[200]["reviewed"] is False
    assert "repositoryId" in prs_by_number[200]

    # The unreviewed PR's placeholder risk doesn't skew the high-risk count,
    # and averages only account for the one real (cached) review.
    assert body["stats"]["highRiskPRs"] == 0
    assert body["stats"]["avgDeploymentConfidence"] == 95


async def test_on_demand_review_endpoint_reviews_specific_pr(client, monkeypatch):
    _patch_github_base(monkeypatch)

    async def fake_list_pull_request_files(self, full_name, number):
        return [GitHubPullRequestFile(filename="a.py", status="modified", additions=5, deletions=1, changes=6)]

    async def fake_get_pull_request(self, full_name, number):
        from app.integrations.github.schemas import GitHubPullRequestDetail

        return GitHubPullRequestDetail(
            number=number,
            title="PR",
            state="open",
            user_login="a",
            html_url="https://github.com/x/pull/1",
            created_at=NOW,
            updated_at=NOW,
            body="",
            base_branch="main",
            head_branch="feat/x",
            additions=5,
            deletions=1,
            changed_files=1,
        )

    async def fake_get_pull_request_diff(self, full_name, number):
        return "diff --git a/a.py b/a.py\n+x\n"

    async def fake_list_pull_request_commits(self, full_name, number):
        return []

    review_output = PRReviewOutput(
        executive_summary=ExecutiveSummary(summary="Risky change."),
        risk_assessment=RiskAssessment(score=80, level=RiskLevel.HIGH, rationale="Touches auth."),
        deployment_confidence=DeploymentConfidence(score=40, rationale="Needs tests."),
        technical_debt=TechnicalDebt(summary="None."),
        breaking_changes=BreakingChangeAssessment(detected=False),
        recommendation=Recommendation.REQUEST_CHANGES,
        recommendation_rationale="Add tests first.",
    )

    async def fake_run_prompt(self, **kwargs):
        return review_output

    monkeypatch.setattr(GitHubClient, "list_pull_request_files", fake_list_pull_request_files)
    monkeypatch.setattr(GitHubClient, "get_pull_request", fake_get_pull_request)
    monkeypatch.setattr(GitHubClient, "get_pull_request_diff", fake_get_pull_request_diff)
    monkeypatch.setattr(GitHubClient, "list_pull_request_commits", fake_list_pull_request_commits)
    monkeypatch.setattr(ContinuumClient, "run_prompt", fake_run_prompt)

    headers = await _register_and_login(client)
    repo_id = await _connect_and_track(client, headers)

    response = await client.post(
        f"/api/development-intelligence/repositories/{repo_id}/pulls/482/review", headers=headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body["number"] == 482
    assert body["risk"] == "high"
    assert body["deploymentConfidence"] == 40
    assert body["reviewed"] is True
    assert body["linesAdded"] == 5


async def test_dev_summary_with_no_tracked_repos_returns_empty_lists(client, monkeypatch):
    headers = await _register_and_login(client)
    response = await client.get("/api/development-intelligence/summary", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["pullRequests"] == []
    assert body["stats"]["openPRs"] == 0


async def test_dev_summary_requires_auth(client):
    response = await client.get("/api/development-intelligence/summary")
    assert response.status_code == 401


async def test_branches_returns_shaped_list(client, monkeypatch):
    _patch_github_base(monkeypatch)

    async def fake_list_branches(self, full_name):
        return [
            GitHubBranch(name="main", sha="abc", protected=True, last_commit_author="a.torres", last_commit_at=NOW),
        ]

    monkeypatch.setattr(GitHubClient, "list_branches", fake_list_branches)

    headers = await _register_and_login(client)
    await _connect_and_track(client, headers)

    response = await client.get("/api/development-intelligence/branches", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body[0]["name"] == "main"
    assert body[0]["author"] == "a.torres"
    assert body[0]["isProtected"] is True


async def test_branches_with_no_tracked_repo_returns_404(client):
    headers = await _register_and_login(client)
    response = await client.get("/api/development-intelligence/branches", headers=headers)
    assert response.status_code == 404


async def _start_and_poll_compare(client, headers, base: str, head: str) -> dict:
    start_response = await client.post(
        "/api/development-intelligence/compare/jobs",
        params={"base": base, "head": head},
        headers=headers,
    )
    assert start_response.status_code == 202
    job_id = start_response.json()["jobId"]

    for _ in range(20):
        status_response = await client.get(
            f"/api/development-intelligence/compare/jobs/{job_id}", headers=headers
        )
        assert status_response.status_code == 200
        job = status_response.json()
        if job["status"] in ("completed", "failed"):
            return job
        await asyncio.sleep(0.01)

    raise AssertionError("compare job never resolved")


async def test_compare_identical_branches(client, monkeypatch):
    _patch_github_base(monkeypatch)
    headers = await _register_and_login(client)
    await _connect_and_track(client, headers)

    job = await _start_and_poll_compare(client, headers, "main", "main")
    assert job["status"] == "completed"
    body = job["result"]
    assert body["identical"] is True
    assert body["mergeScore"] == 100
    assert body["recommendation"] == "merge"


async def test_compare_different_branches(client, monkeypatch):
    _patch_github_base(monkeypatch)

    async def fake_compare_branches(self, full_name, base, head):
        return GitHubComparison(
            base=base,
            head=head,
            status="ahead",
            ahead_by=8,
            behind_by=2,
            total_commits=8,
            additions=320,
            deletions=118,
            files=[
                GitHubComparisonFile(
                    filename="src/payments/retry.ts",
                    status="modified",
                    additions=164,
                    deletions=72,
                    changes=236,
                    patch="@@ -1,3 +1,3 @@\n-old\n+new",
                )
            ],
        )

    monkeypatch.setattr(GitHubClient, "compare_branches", fake_compare_branches)

    review_output = CompareReviewOutput(
        summary="Rewrites retry logic.",
        risk_score=75,
        risk_level=RiskLevel.HIGH,
        deployment_confidence=55,
        recommendation=Recommendation.APPROVE_WITH_CHANGES,
        findings=[
            Finding(title="Possible race condition", description="Retry loop isn't idempotent.", severity="high")
        ],
    )

    async def fake_run_prompt(self, **kwargs):
        return review_output

    monkeypatch.setattr(ContinuumClient, "run_prompt", fake_run_prompt)

    headers = await _register_and_login(client)
    await _connect_and_track(client, headers)

    job = await _start_and_poll_compare(client, headers, "main", "feat/payment-retry")
    assert job["status"] == "completed"
    body = job["result"]
    assert body["identical"] is False
    assert body["commitsAhead"] == 8
    assert body["risk"] == "high"
    assert body["deploymentConfidence"] == 55
    assert "race condition" in body["risks"][0].lower()
    assert body["gains"] == ["Incorporates 8 commit(s) not yet on main"]
    assert body["changedFiles"][0]["path"] == "src/payments/retry.ts"


async def test_compare_job_reports_failure(client, monkeypatch):
    _patch_github_base(monkeypatch)

    async def fake_compare_branches(self, full_name, base, head):
        return GitHubComparison(
            base=base, head=head, status="ahead", ahead_by=1, behind_by=0, total_commits=1,
            files=[GitHubComparisonFile(filename="a.py", status="modified", additions=1, deletions=0, changes=1)],
        )

    async def failing_run_prompt(self, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(GitHubClient, "compare_branches", fake_compare_branches)
    monkeypatch.setattr(ContinuumClient, "run_prompt", failing_run_prompt)

    headers = await _register_and_login(client)
    await _connect_and_track(client, headers)

    job = await _start_and_poll_compare(client, headers, "main", "feat/x")
    assert job["status"] == "failed"
    assert job["error"]
    assert job["result"] is None


async def test_compare_job_not_found_returns_404(client):
    headers = await _register_and_login(client)
    response = await client.get(
        "/api/development-intelligence/compare/jobs/00000000-0000-0000-0000-000000000000", headers=headers
    )
    assert response.status_code == 404
