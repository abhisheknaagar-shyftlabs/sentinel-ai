import uuid

from app.integrations.github.client import GitHubClient
from app.integrations.github.schemas import (
    GitHubBranch,
    GitHubComparison,
    GitHubRepo,
    GitHubUser,
)
from app.services.github_service import GitHubIntegrationService
from tests.test_github import _register_and_login


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


async def test_service_list_branches_and_compare(client, db_session, monkeypatch):
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

    async def fake_list_branches(self, full_name):
        return [GitHubBranch(name="main", sha="abc", protected=True, last_commit_author="octocat")]

    async def fake_compare_branches(self, full_name, base, head):
        return GitHubComparison(base=base, head=head, status="ahead", ahead_by=3, behind_by=0, total_commits=3)

    monkeypatch.setattr(GitHubClient, "get_authenticated_user", fake_get_authenticated_user)
    monkeypatch.setattr(GitHubClient, "get_repository", fake_get_repository)
    monkeypatch.setattr(GitHubClient, "list_branches", fake_list_branches)
    monkeypatch.setattr(GitHubClient, "compare_branches", fake_compare_branches)

    headers = await _register_and_login(client)
    repository_id = await _connect_and_track(client, headers)

    me_response = await client.get("/api/v1/auth/me", headers=headers)
    user_id = uuid.UUID(me_response.json()["data"]["id"])

    service = GitHubIntegrationService(db_session)
    branches = await service.list_branches(user_id, uuid.UUID(repository_id))
    assert branches[0].name == "main"

    comparison = await service.compare_branches(user_id, uuid.UUID(repository_id), "main", "feat/x")
    assert comparison.ahead_by == 3
