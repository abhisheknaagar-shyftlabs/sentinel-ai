from typing import Any

import httpx

from app.integrations.github.exceptions import (
    GitHubAPIError,
    GitHubAuthError,
    GitHubNotFoundError,
    GitHubRateLimitError,
)
from app.integrations.github.exceptions import GitHubError
from app.integrations.github.schemas import (
    GitHubBranch,
    GitHubCommit,
    GitHubComparison,
    GitHubComparisonFile,
    GitHubPullRequestDetail,
    GitHubPullRequestFile,
    GitHubPullRequestSummary,
    GitHubRepo,
    GitHubUser,
)

GITHUB_API_BASE_URL = "https://api.github.com"
GITHUB_API_VERSION = "2022-11-28"


class GitHubClient:
    """Thin, typed wrapper around the GitHub REST API. Holds one user's PAT —
    instantiate per-request, never share an instance across users."""

    def __init__(
        self,
        access_token: str,
        timeout: float = 15.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._access_token = access_token
        self._timeout = timeout
        self._transport = transport

    def _headers(self, accept: str = "application/vnd.github+json") -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Accept": accept,
            "X-GitHub-Api-Version": GITHUB_API_VERSION,
        }

    async def _request(
        self,
        method: str,
        path: str,
        *,
        accept: str | None = None,
        params: dict[str, Any] | None = None,
    ) -> httpx.Response:
        async with httpx.AsyncClient(
            base_url=GITHUB_API_BASE_URL, timeout=self._timeout, transport=self._transport
        ) as client:
            response = await client.request(method, path, headers=self._headers(accept or "application/vnd.github+json"), params=params)

        if response.status_code == 401:
            raise GitHubAuthError("GitHub rejected the provided token")
        if response.status_code == 403 and response.headers.get("X-RateLimit-Remaining") == "0":
            raise GitHubRateLimitError("GitHub API rate limit exceeded")
        if response.status_code == 404:
            raise GitHubNotFoundError(f"GitHub resource not found: {path}")
        if response.status_code >= 400:
            raise GitHubAPIError(f"GitHub API error {response.status_code}: {response.text[:200]}")

        return response

    async def get_authenticated_user(self) -> tuple[GitHubUser, list[str]]:
        response = await self._request("GET", "/user")
        data = response.json()
        scopes_header = response.headers.get("X-OAuth-Scopes", "")
        scopes = [s.strip() for s in scopes_header.split(",") if s.strip()]
        user = GitHubUser(
            login=data["login"],
            id=data["id"],
            type=data["type"],
            name=data.get("name"),
            avatar_url=data.get("avatar_url"),
        )
        return user, scopes

    async def list_repositories(self) -> list[GitHubRepo]:
        response = await self._request("GET", "/user/repos", params={"per_page": 100, "sort": "updated"})
        return [_map_repo(item) for item in response.json()]

    async def get_repository(self, full_name: str) -> GitHubRepo:
        response = await self._request("GET", f"/repos/{full_name}")
        return _map_repo(response.json())

    async def list_pull_requests(self, full_name: str, state: str = "open") -> list[GitHubPullRequestSummary]:
        response = await self._request(
            "GET", f"/repos/{full_name}/pulls", params={"state": state, "per_page": 100}
        )
        return [_map_pr_summary(item) for item in response.json()]

    async def get_pull_request(self, full_name: str, number: int) -> GitHubPullRequestDetail:
        response = await self._request("GET", f"/repos/{full_name}/pulls/{number}")
        return _map_pr_detail(response.json())

    async def get_pull_request_diff(self, full_name: str, number: int) -> str:
        response = await self._request(
            "GET", f"/repos/{full_name}/pulls/{number}", accept="application/vnd.github.v3.diff"
        )
        return response.text

    async def list_pull_request_files(self, full_name: str, number: int) -> list[GitHubPullRequestFile]:
        response = await self._request(
            "GET", f"/repos/{full_name}/pulls/{number}/files", params={"per_page": 100}
        )
        return [
            GitHubPullRequestFile(
                filename=item["filename"],
                status=item["status"],
                additions=item["additions"],
                deletions=item["deletions"],
                changes=item["changes"],
                patch=item.get("patch"),
            )
            for item in response.json()
        ]

    async def list_pull_request_commits(self, full_name: str, number: int) -> list[GitHubCommit]:
        response = await self._request(
            "GET", f"/repos/{full_name}/pulls/{number}/commits", params={"per_page": 100}
        )
        return [_map_commit(item) for item in response.json()]

    async def list_branches(self, full_name: str) -> list[GitHubBranch]:
        response = await self._request("GET", f"/repos/{full_name}/branches", params={"per_page": 100})
        branches = []
        for item in response.json():
            author, committed_at = await self._get_branch_last_commit_info(full_name, item["name"])
            branches.append(
                GitHubBranch(
                    name=item["name"],
                    sha=item["commit"]["sha"],
                    protected=item.get("protected", False),
                    last_commit_author=author,
                    last_commit_at=committed_at,
                )
            )
        return branches

    async def _get_branch_last_commit_info(
        self, full_name: str, branch_name: str
    ) -> tuple[str | None, str | None]:
        try:
            response = await self._request(
                "GET", f"/repos/{full_name}/commits", params={"sha": branch_name, "per_page": 1}
            )
        except GitHubError:
            return None, None
        items = response.json()
        if not items:
            return None, None
        item = items[0]
        commit_author = item.get("commit", {}).get("author", {}) or {}
        login = (item.get("author") or {}).get("login")
        return login or commit_author.get("name"), commit_author.get("date")

    async def compare_branches(self, full_name: str, base: str, head: str) -> GitHubComparison:
        response = await self._request("GET", f"/repos/{full_name}/compare/{base}...{head}")
        data = response.json()
        files = data.get("files") or []
        return GitHubComparison(
            base=base,
            head=head,
            status=data.get("status", "identical"),
            ahead_by=data.get("ahead_by", 0),
            behind_by=data.get("behind_by", 0),
            total_commits=data.get("total_commits", 0),
            additions=sum(f.get("additions", 0) for f in files),
            deletions=sum(f.get("deletions", 0) for f in files),
            files=[
                GitHubComparisonFile(
                    filename=f["filename"],
                    status=f["status"],
                    additions=f["additions"],
                    deletions=f["deletions"],
                    changes=f["changes"],
                    patch=f.get("patch"),
                )
                for f in files
            ],
        )


def _map_repo(item: dict[str, Any]) -> GitHubRepo:
    return GitHubRepo(
        id=item["id"],
        name=item["name"],
        full_name=item["full_name"],
        private=item["private"],
        default_branch=item.get("default_branch", "main"),
        html_url=item["html_url"],
        description=item.get("description"),
        updated_at=item.get("updated_at"),
    )


def _map_pr_summary(item: dict[str, Any]) -> GitHubPullRequestSummary:
    return GitHubPullRequestSummary(
        number=item["number"],
        title=item["title"],
        state=item["state"],
        user_login=item["user"]["login"],
        html_url=item["html_url"],
        created_at=item["created_at"],
        updated_at=item["updated_at"],
        draft=item.get("draft", False),
        base_branch=item["base"]["ref"],
        head_branch=item["head"]["ref"],
    )


def _map_pr_detail(item: dict[str, Any]) -> GitHubPullRequestDetail:
    return GitHubPullRequestDetail(
        number=item["number"],
        title=item["title"],
        state=item["state"],
        user_login=item["user"]["login"],
        html_url=item["html_url"],
        created_at=item["created_at"],
        updated_at=item["updated_at"],
        draft=item.get("draft", False),
        base_branch=item["base"]["ref"],
        head_branch=item["head"]["ref"],
        body=item.get("body"),
        additions=item.get("additions", 0),
        deletions=item.get("deletions", 0),
        changed_files=item.get("changed_files", 0),
        mergeable=item.get("mergeable"),
        merged=item.get("merged", False),
    )


def _map_commit(item: dict[str, Any]) -> GitHubCommit:
    commit = item["commit"]
    author = commit.get("author") or {}
    return GitHubCommit(
        sha=item["sha"],
        message=commit["message"],
        author_name=author.get("name"),
        author_email=author.get("email"),
        committed_at=author.get("date"),
        html_url=item["html_url"],
    )
