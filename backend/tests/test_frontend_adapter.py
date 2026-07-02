from app.integrations.docker.client import DockerClient
from app.integrations.github.client import GitHubClient
from app.integrations.github.schemas import GitHubUser
from tests.test_github import _register_and_login


async def test_frontend_login_returns_contract_shape(client):
    await client.post(
        "/api/v1/auth/register", json={"email": "frontend@sentinel.ai", "password": "supersecret123"}
    )
    response = await client.post(
        "/api/auth/login", json={"email": "frontend@sentinel.ai", "password": "supersecret123"}
    )
    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"token", "user"}
    assert set(body["user"].keys()) == {"name", "email", "workspace"}
    assert body["user"]["email"] == "frontend@sentinel.ai"
    assert body["user"]["workspace"] == "My Workspace"


async def test_frontend_login_bad_credentials_returns_401(client):
    response = await client.post(
        "/api/auth/login", json={"email": "nope@sentinel.ai", "password": "wrong"}
    )
    assert response.status_code == 401


async def test_frontend_settings_get_and_patch_roundtrip(client):
    headers = await _register_and_login(client)

    get_response = await client.get("/api/settings", headers=headers)
    assert get_response.status_code == 200
    body = get_response.json()
    assert set(body.keys()) == {"workspace", "notifications", "aiPreferences"}
    assert body["workspace"]["workspaceName"] == "My Workspace"

    patch_response = await client.patch(
        "/api/settings/workspace",
        json={"workspaceName": "Acme Engineering", "timezone": "America/New_York", "defaultBranch": "main"},
        headers=headers,
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["workspace"]["workspaceName"] == "Acme Engineering"

    refetch = await client.get("/api/settings", headers=headers)
    assert refetch.json()["workspace"]["workspaceName"] == "Acme Engineering"


async def test_frontend_settings_unknown_section_returns_404(client):
    headers = await _register_and_login(client)
    response = await client.patch("/api/settings/nonsense", json={}, headers=headers)
    assert response.status_code == 404


async def test_frontend_settings_requires_auth(client):
    response = await client.get("/api/settings")
    assert response.status_code == 401


async def test_frontend_integrations_shows_github_and_docker_only(client, monkeypatch):
    async def fake_get_authenticated_user(self):
        return GitHubUser(login="octocat", id=1, type="User"), ["repo"]

    async def fake_health(self):
        return True

    monkeypatch.setattr(GitHubClient, "get_authenticated_user", fake_get_authenticated_user)
    monkeypatch.setattr(DockerClient, "health", fake_health)

    headers = await _register_and_login(client)
    await client.post(
        "/api/v1/github/integrations", json={"personal_access_token": "ghp_fake"}, headers=headers
    )

    response = await client.get("/api/integrations", headers=headers)
    assert response.status_code == 200
    body = response.json()
    ids = [item["id"] for item in body]
    assert ids == ["github", "docker"]
    github_entry = next(item for item in body if item["id"] == "github")
    assert github_entry["status"] == "connected"
    assert github_entry["connectedAccount"] == "octocat"
    docker_entry = next(item for item in body if item["id"] == "docker")
    assert docker_entry["status"] == "connected"


async def test_frontend_integrations_disconnected_when_nothing_connected(client, monkeypatch):
    async def fake_health(self):
        raise RuntimeError("daemon unreachable")

    monkeypatch.setattr(DockerClient, "health", fake_health)

    headers = await _register_and_login(client)
    response = await client.get("/api/integrations", headers=headers)
    body = response.json()
    assert body[0]["status"] == "disconnected"
    assert body[1]["status"] == "disconnected"


async def test_frontend_connect_github_with_valid_pat(client, monkeypatch):
    async def fake_get_authenticated_user(self):
        return GitHubUser(login="octocat", id=1, type="User"), ["repo"]

    monkeypatch.setattr(GitHubClient, "get_authenticated_user", fake_get_authenticated_user)

    headers = await _register_and_login(client)
    response = await client.post(
        "/api/integrations/github/connect",
        json={"personalAccessToken": "ghp_fake"},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "connected"
    assert body["connectedAccount"] == "octocat"

    list_response = await client.get("/api/integrations", headers=headers)
    github_entry = next(item for item in list_response.json() if item["id"] == "github")
    assert github_entry["status"] == "connected"


async def test_frontend_connect_github_also_tracks_requested_repo(client, monkeypatch):
    from app.integrations.github.schemas import GitHubRepo

    async def fake_get_authenticated_user(self):
        return GitHubUser(login="octocat", id=1, type="User"), ["repo"]

    async def fake_get_repository(self, full_name):
        return GitHubRepo(
            id=555,
            name="express",
            full_name=full_name,
            private=False,
            default_branch="main",
            html_url=f"https://github.com/{full_name}",
            description=None,
        )

    monkeypatch.setattr(GitHubClient, "get_authenticated_user", fake_get_authenticated_user)
    monkeypatch.setattr(GitHubClient, "get_repository", fake_get_repository)

    headers = await _register_and_login(client)
    response = await client.post(
        "/api/integrations/github/connect",
        json={"personalAccessToken": "ghp_fake", "repositoryFullName": "expressjs/express"},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "connected"
    assert body["repositoryTracked"] == "expressjs/express"
    assert body["repositoryError"] is None

    tracked_response = await client.get("/api/v1/github/repositories", headers=headers)
    tracked = tracked_response.json()["data"]
    assert any(r["full_name"] == "expressjs/express" for r in tracked)


async def test_frontend_connect_github_repo_tracking_failure_does_not_fail_connect(client, monkeypatch):
    async def fake_get_authenticated_user(self):
        return GitHubUser(login="octocat", id=1, type="User"), ["repo"]

    async def fake_get_repository(self, full_name):
        from app.integrations.github.exceptions import GitHubNotFoundError

        raise GitHubNotFoundError(f"/repos/{full_name}")

    monkeypatch.setattr(GitHubClient, "get_authenticated_user", fake_get_authenticated_user)
    monkeypatch.setattr(GitHubClient, "get_repository", fake_get_repository)

    headers = await _register_and_login(client)
    response = await client.post(
        "/api/integrations/github/connect",
        json={"personalAccessToken": "ghp_fake", "repositoryFullName": "nope/does-not-exist"},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "connected"
    assert body["repositoryTracked"] is None
    assert body["repositoryError"] is not None


async def test_frontend_connect_github_with_bad_pat_returns_401(client, monkeypatch):
    from app.integrations.github.exceptions import GitHubAuthError

    async def fake_get_authenticated_user(self):
        raise GitHubAuthError("bad token")

    monkeypatch.setattr(GitHubClient, "get_authenticated_user", fake_get_authenticated_user)

    headers = await _register_and_login(client)
    response = await client.post(
        "/api/integrations/github/connect",
        json={"personalAccessToken": "ghp_bad"},
        headers=headers,
    )
    assert response.status_code == 401


async def test_frontend_connect_github_without_token_returns_422(client):
    headers = await _register_and_login(client)
    response = await client.post("/api/integrations/github/connect", json={}, headers=headers)
    assert response.status_code == 422


async def test_frontend_connect_docker_not_supported(client):
    headers = await _register_and_login(client)
    response = await client.post(
        "/api/integrations/docker/connect", json={"personalAccessToken": "x"}, headers=headers
    )
    assert response.status_code == 422


async def test_frontend_disconnect_github(client, monkeypatch):
    async def fake_get_authenticated_user(self):
        return GitHubUser(login="octocat", id=1, type="User"), ["repo"]

    monkeypatch.setattr(GitHubClient, "get_authenticated_user", fake_get_authenticated_user)

    headers = await _register_and_login(client)
    await client.post(
        "/api/integrations/github/connect", json={"personalAccessToken": "ghp_fake"}, headers=headers
    )

    response = await client.post("/api/integrations/github/disconnect", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "disconnected"
