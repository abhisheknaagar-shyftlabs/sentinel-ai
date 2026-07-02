from datetime import datetime, timezone

from app.integrations.github.client import GitHubClient
from app.integrations.github.exceptions import GitHubAuthError
from app.integrations.github.schemas import GitHubPullRequestSummary, GitHubRepo, GitHubUser


async def _register_and_login(client):
    payload = {"email": "gh@sentinel.ai", "password": "supersecret123"}
    response = await client.post("/api/v1/auth/register", json=payload)
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def test_connect_integration(client, monkeypatch):
    async def fake_get_authenticated_user(self):
        return GitHubUser(login="octocat", id=1, type="User"), ["repo"]

    monkeypatch.setattr(GitHubClient, "get_authenticated_user", fake_get_authenticated_user)

    headers = await _register_and_login(client)
    response = await client.post(
        "/api/v1/github/integrations", json={"personal_access_token": "ghp_fake"}, headers=headers
    )
    assert response.status_code == 201
    body = response.json()["data"]
    assert body["account_login"] == "octocat"
    assert "access_token_encrypted" not in body
    assert "personal_access_token" not in body


async def test_connect_integration_invalid_token(client, monkeypatch):
    async def fake_get_authenticated_user(self):
        raise GitHubAuthError("bad token")

    monkeypatch.setattr(GitHubClient, "get_authenticated_user", fake_get_authenticated_user)

    headers = await _register_and_login(client)
    response = await client.post(
        "/api/v1/github/integrations", json={"personal_access_token": "bad"}, headers=headers
    )
    assert response.status_code == 401
    assert response.json()["success"] is False


async def test_track_repository_and_list_pull_requests(client, monkeypatch):
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

    async def fake_list_pull_requests(self, full_name, state="open"):
        now = datetime.now(timezone.utc)
        return [
            GitHubPullRequestSummary(
                number=1,
                title="Add feature",
                state="open",
                user_login="octocat",
                html_url=f"https://github.com/{full_name}/pull/1",
                created_at=now,
                updated_at=now,
                base_branch="main",
                head_branch="feat/add-feature",
            )
        ]

    monkeypatch.setattr(GitHubClient, "get_authenticated_user", fake_get_authenticated_user)
    monkeypatch.setattr(GitHubClient, "get_repository", fake_get_repository)
    monkeypatch.setattr(GitHubClient, "list_pull_requests", fake_list_pull_requests)

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
    assert track_response.status_code == 201
    repository_id = track_response.json()["data"]["id"]

    duplicate_response = await client.post(
        f"/api/v1/github/integrations/{integration_id}/repositories",
        json={"full_name": "octocat/sentinel-ai"},
        headers=headers,
    )
    assert duplicate_response.status_code == 409

    pulls_response = await client.get(f"/api/v1/github/repositories/{repository_id}/pulls", headers=headers)
    assert pulls_response.status_code == 200
    prs = pulls_response.json()["data"]
    assert len(prs) == 1
    assert prs[0]["number"] == 1

    tracked_response = await client.get("/api/v1/github/repositories", headers=headers)
    assert len(tracked_response.json()["data"]) == 1


async def test_pull_request_for_unowned_repository_returns_404(client, monkeypatch):
    async def fake_get_authenticated_user(self):
        return GitHubUser(login="octocat", id=1, type="User"), ["repo"]

    monkeypatch.setattr(GitHubClient, "get_authenticated_user", fake_get_authenticated_user)

    headers = await _register_and_login(client)
    response = await client.get(
        "/api/v1/github/repositories/00000000-0000-0000-0000-000000000000/pulls", headers=headers
    )
    assert response.status_code == 404


async def test_unauthenticated_requests_rejected(client):
    response = await client.get("/api/v1/github/repositories")
    assert response.status_code == 401
