import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, UnauthorizedError
from app.integrations.github.client import GitHubClient
from app.integrations.github.exceptions import (
    GitHubAuthError,
    GitHubError,
    GitHubNotFoundError,
    GitHubRateLimitError,
)
from app.integrations.github.schemas import (
    GitHubBranch,
    GitHubComparison,
    GitHubCommit,
    GitHubPullRequestDetail,
    GitHubPullRequestFile,
    GitHubPullRequestSummary,
    GitHubRepo,
)
from app.models.integration import Integration
from app.models.repository import TrackedRepository
from app.repositories.integration_repository import IntegrationRepository
from app.repositories.tracked_repository_repository import TrackedRepositoryRepository
from app.schemas.integration import IntegrationCreate
from app.schemas.repository import RepositoryTrackRequest
from app.security.encryption import decrypt_secret, encrypt_secret
from app.utils.time import utc_now


class GitHubIntegrationService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.integrations = IntegrationRepository(session)
        self.tracked_repos = TrackedRepositoryRepository(session)

    async def connect_integration(self, user_id: uuid.UUID, payload: IntegrationCreate) -> Integration:
        client = GitHubClient(access_token=payload.personal_access_token)
        try:
            github_user, scopes = await client.get_authenticated_user()
        except GitHubAuthError as exc:
            raise UnauthorizedError("The provided GitHub token is invalid or expired") from exc
        except GitHubError as exc:
            raise ConflictError(f"Could not validate GitHub token: {exc}") from exc

        integration = Integration(
            user_id=user_id,
            workspace_id=payload.workspace_id,
            provider="github",
            account_login=github_user.login,
            account_type=github_user.type,
            scopes=",".join(scopes) if scopes else None,
            access_token_encrypted=encrypt_secret(payload.personal_access_token),
            is_active=True,
            last_validated_at=utc_now(),
        )
        return await self.integrations.create(integration)

    async def list_integrations(self, user_id: uuid.UUID) -> list[Integration]:
        return await self.integrations.list_for_user(user_id)

    async def disconnect_integration(self, user_id: uuid.UUID, integration_id: uuid.UUID) -> None:
        integration = await self._get_owned_integration(integration_id, user_id)
        await self.integrations.delete(integration)

    async def list_available_repositories(
        self, user_id: uuid.UUID, integration_id: uuid.UUID
    ) -> list[GitHubRepo]:
        integration = await self._get_owned_integration(integration_id, user_id)
        client = self._client_for(integration)
        return await self._call(client.list_repositories)

    async def track_repository(
        self, user_id: uuid.UUID, integration_id: uuid.UUID, payload: RepositoryTrackRequest
    ) -> TrackedRepository:
        integration = await self._get_owned_integration(integration_id, user_id)
        client = self._client_for(integration)
        repo = await self._call(client.get_repository, payload.full_name)

        existing = await self.tracked_repos.get_by_github_id(integration.id, repo.id)
        if existing is not None:
            raise ConflictError(f"Repository '{repo.full_name}' is already tracked")

        tracked = TrackedRepository(
            integration_id=integration.id,
            github_id=repo.id,
            name=repo.name,
            full_name=repo.full_name,
            private=repo.private,
            default_branch=repo.default_branch,
            html_url=repo.html_url,
            description=repo.description,
            last_synced_at=utc_now(),
        )
        return await self.tracked_repos.create(tracked)

    async def list_tracked_repositories(self, user_id: uuid.UUID) -> list[TrackedRepository]:
        return await self.tracked_repos.list_for_user(user_id)

    async def list_pull_requests(
        self, user_id: uuid.UUID, repository_id: uuid.UUID, state: str = "open"
    ) -> list[GitHubPullRequestSummary]:
        repo, client = await self._resolve_repo_and_client(user_id, repository_id)
        return await self._call(client.list_pull_requests, repo.full_name, state)

    async def get_pull_request(
        self, user_id: uuid.UUID, repository_id: uuid.UUID, number: int
    ) -> GitHubPullRequestDetail:
        repo, client = await self._resolve_repo_and_client(user_id, repository_id)
        return await self._call(client.get_pull_request, repo.full_name, number)

    async def get_pull_request_diff(self, user_id: uuid.UUID, repository_id: uuid.UUID, number: int) -> str:
        repo, client = await self._resolve_repo_and_client(user_id, repository_id)
        return await self._call(client.get_pull_request_diff, repo.full_name, number)

    async def list_pull_request_files(
        self, user_id: uuid.UUID, repository_id: uuid.UUID, number: int
    ) -> list[GitHubPullRequestFile]:
        repo, client = await self._resolve_repo_and_client(user_id, repository_id)
        return await self._call(client.list_pull_request_files, repo.full_name, number)

    async def list_pull_request_commits(
        self, user_id: uuid.UUID, repository_id: uuid.UUID, number: int
    ) -> list[GitHubCommit]:
        repo, client = await self._resolve_repo_and_client(user_id, repository_id)
        return await self._call(client.list_pull_request_commits, repo.full_name, number)

    async def list_branches(self, user_id: uuid.UUID, repository_id: uuid.UUID) -> list[GitHubBranch]:
        repo, client = await self._resolve_repo_and_client(user_id, repository_id)
        return await self._call(client.list_branches, repo.full_name)

    async def compare_branches(
        self, user_id: uuid.UUID, repository_id: uuid.UUID, base: str, head: str
    ) -> GitHubComparison:
        repo, client = await self._resolve_repo_and_client(user_id, repository_id)
        return await self._call(client.compare_branches, repo.full_name, base, head)

    async def _resolve_repo_and_client(
        self, user_id: uuid.UUID, repository_id: uuid.UUID
    ) -> tuple[TrackedRepository, GitHubClient]:
        repo = await self.tracked_repos.get_for_user(repository_id, user_id)
        if repo is None:
            raise NotFoundError("Tracked repository not found")
        integration = await self.integrations.get_by_id(repo.integration_id)
        if integration is None or integration.user_id != user_id:
            raise NotFoundError("Tracked repository not found")
        return repo, self._client_for(integration)

    async def _get_owned_integration(self, integration_id: uuid.UUID, user_id: uuid.UUID) -> Integration:
        integration = await self.integrations.get_for_user(integration_id, user_id)
        if integration is None:
            raise NotFoundError("Integration not found")
        return integration

    def _client_for(self, integration: Integration) -> GitHubClient:
        token = decrypt_secret(integration.access_token_encrypted)
        return GitHubClient(access_token=token)

    @staticmethod
    async def _call(fn: Any, *args: Any) -> Any:
        try:
            return await fn(*args)
        except GitHubAuthError as exc:
            raise UnauthorizedError("GitHub token is no longer valid") from exc
        except GitHubNotFoundError as exc:
            raise NotFoundError(str(exc)) from exc
        except GitHubRateLimitError as exc:
            raise ForbiddenError("GitHub API rate limit exceeded, try again later") from exc
        except GitHubError as exc:
            raise ConflictError(f"GitHub API error: {exc}") from exc
