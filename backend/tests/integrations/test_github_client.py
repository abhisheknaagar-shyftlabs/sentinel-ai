import httpx
import pytest

from app.integrations.github.client import GitHubClient
from app.integrations.github.exceptions import GitHubAuthError, GitHubNotFoundError, GitHubRateLimitError


def _transport(handler):
    return httpx.MockTransport(handler)


async def test_get_authenticated_user():
    def handler(request):
        assert request.headers["authorization"] == "Bearer test-token"
        return httpx.Response(
            200,
            json={"login": "octocat", "id": 1, "type": "User", "name": "Octo Cat"},
            headers={"X-OAuth-Scopes": "repo, read:org"},
        )

    client = GitHubClient(access_token="test-token", transport=_transport(handler))
    user, scopes = await client.get_authenticated_user()
    assert user.login == "octocat"
    assert scopes == ["repo", "read:org"]


async def test_invalid_token_raises_auth_error():
    def handler(request):
        return httpx.Response(401, json={"message": "Bad credentials"})

    client = GitHubClient(access_token="bad-token", transport=_transport(handler))
    with pytest.raises(GitHubAuthError):
        await client.get_authenticated_user()


async def test_not_found_raises():
    def handler(request):
        return httpx.Response(404, json={"message": "Not Found"})

    client = GitHubClient(access_token="token", transport=_transport(handler))
    with pytest.raises(GitHubNotFoundError):
        await client.get_repository("owner/missing")


async def test_rate_limit_raises():
    def handler(request):
        return httpx.Response(403, headers={"X-RateLimit-Remaining": "0"}, json={"message": "rate limited"})

    client = GitHubClient(access_token="token", transport=_transport(handler))
    with pytest.raises(GitHubRateLimitError):
        await client.list_repositories()


async def test_list_repositories_maps_fields():
    def handler(request):
        return httpx.Response(
            200,
            json=[
                {
                    "id": 123,
                    "name": "sentinel-ai",
                    "full_name": "octocat/sentinel-ai",
                    "private": False,
                    "default_branch": "main",
                    "html_url": "https://github.com/octocat/sentinel-ai",
                    "description": "desc",
                    "updated_at": "2026-01-01T00:00:00Z",
                }
            ],
        )

    client = GitHubClient(access_token="token", transport=_transport(handler))
    repos = await client.list_repositories()
    assert len(repos) == 1
    assert repos[0].full_name == "octocat/sentinel-ai"


async def test_get_pull_request_diff_returns_raw_text():
    def handler(request):
        assert request.headers["accept"] == "application/vnd.github.v3.diff"
        return httpx.Response(200, text="diff --git a/x b/x\n+added line\n")

    client = GitHubClient(access_token="token", transport=_transport(handler))
    diff = await client.get_pull_request_diff("octocat/sentinel-ai", 1)
    assert "added line" in diff


async def test_list_branches_includes_last_commit_info():
    def handler(request):
        if request.url.path.endswith("/branches"):
            return httpx.Response(
                200,
                json=[
                    {"name": "main", "commit": {"sha": "abc123"}, "protected": True},
                    {"name": "feat/x", "commit": {"sha": "def456"}, "protected": False},
                ],
            )
        # GET .../commits?sha=<branch>&per_page=1
        branch = request.url.params.get("sha")
        return httpx.Response(
            200,
            json=[
                {
                    "author": {"login": f"user-of-{branch}"},
                    "commit": {"author": {"name": "Some Name", "date": "2026-07-01T09:59:00Z"}},
                }
            ],
        )

    client = GitHubClient(access_token="token", transport=_transport(handler))
    branches = await client.list_branches("octocat/sentinel-ai")

    assert len(branches) == 2
    assert branches[0].name == "main"
    assert branches[0].protected is True
    assert branches[0].last_commit_author == "user-of-main"
    assert branches[0].last_commit_at is not None


async def test_compare_branches_maps_fields():
    def handler(request):
        assert "/compare/main...feat/x" in str(request.url)
        return httpx.Response(
            200,
            json={
                "status": "ahead",
                "ahead_by": 8,
                "behind_by": 2,
                "total_commits": 8,
                "files": [
                    {"filename": "a.py", "status": "modified", "additions": 10, "deletions": 3, "changes": 13},
                ],
            },
        )

    client = GitHubClient(access_token="token", transport=_transport(handler))
    comparison = await client.compare_branches("octocat/sentinel-ai", "main", "feat/x")

    assert comparison.ahead_by == 8
    assert comparison.additions == 10
    assert comparison.files[0].filename == "a.py"
