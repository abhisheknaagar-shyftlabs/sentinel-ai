import time
import uuid

from app.agents.development.schemas import ChangedFileSummary, CommitSummary, PRReviewInput, PRReviewOutput
from app.continuum.client import ContinuumClient
from app.continuum.exceptions import AgentNotFoundError
from app.core.exceptions import AppException, GatewayTimeoutError, NotFoundError, ServiceUnavailableError, ValidationAppError
from app.core.logging import get_logger
from app.models.ai_fix import AIFix
from app.models.review import AIReview
from app.repositories.ai_fix_repository import AIFixRepository
from app.repositories.ai_review_repository import AIReviewRepository
from app.services.github_service import GitHubIntegrationService
from app.utils.time import utc_now

logger = get_logger(__name__)


class PRReviewService:
    def __init__(
        self,
        github_service: GitHubIntegrationService,
        continuum_client: ContinuumClient,
        review_repository: AIReviewRepository,
        ai_fix_repository: AIFixRepository,
    ) -> None:
        self.github_service = github_service
        self.continuum_client = continuum_client
        self.reviews = review_repository
        self.ai_fixes = ai_fix_repository

    async def review_pull_request(
        self, user_id: uuid.UUID, repository_id: uuid.UUID, pr_number: int
    ) -> PRReviewOutput:
        tracked_repo = await self.github_service.tracked_repos.get_for_user(repository_id, user_id)
        if tracked_repo is None:
            raise NotFoundError("Tracked repository not found")

        pr = await self.github_service.get_pull_request(user_id, repository_id, pr_number)
        diff = await self.github_service.get_pull_request_diff(user_id, repository_id, pr_number)
        files = await self.github_service.list_pull_request_files(user_id, repository_id, pr_number)
        commits = await self.github_service.list_pull_request_commits(user_id, repository_id, pr_number)

        agent_input = PRReviewInput(
            repository_full_name=tracked_repo.full_name,
            pr_number=pr.number,
            title=pr.title,
            description=pr.body,
            base_branch=pr.base_branch,
            head_branch=pr.head_branch,
            diff=diff,
            changed_files=[
                ChangedFileSummary(
                    filename=f.filename,
                    status=f.status,
                    additions=f.additions,
                    deletions=f.deletions,
                    patch=f.patch,
                )
                for f in files
            ],
            commits=[
                CommitSummary(sha=c.sha, message=c.message, author_name=c.author_name) for c in commits
            ],
        )

        start = time.perf_counter()
        try:
            result = await self.continuum_client.run_agent("pr_review", agent_input)
        except AgentNotFoundError as exc:
            raise ServiceUnavailableError("AI review capability is not currently available") from exc
        total_duration_ms = round((time.perf_counter() - start) * 1000, 2)

        logger.info(
            "pr_review_completed" if result.success else "pr_review_failed",
            extra={
                "repository_id": str(repository_id),
                "pull_request_number": pr_number,
                "continuum_latency_ms": result.duration_ms,
                "total_duration_ms": total_duration_ms,
                "success": result.success,
            },
        )

        if not result.success:
            raise self._map_agent_failure(result.error_type, result.error)

        review_output = result.data
        assert isinstance(review_output, PRReviewOutput)

        review = AIReview(
            repository_id=tracked_repo.id,
            pull_request_number=pr_number,
            review_timestamp=utc_now(),
            summary=review_output.executive_summary.summary,
            risk_score=review_output.risk_assessment.score,
            deployment_confidence=review_output.deployment_confidence.score,
            recommendation=review_output.recommendation.value,
            technical_debt_summary=review_output.technical_debt.summary,
        )
        await self.reviews.create(review)

        if review_output.code_fix_suggestions:
            await self.ai_fixes.bulk_create(
                [
                    AIFix(
                        repository_id=tracked_repo.id,
                        pull_request_number=pr_number,
                        file=fix.file,
                        description=fix.description,
                        suggested_patch=fix.suggested_patch,
                        confidence=fix.confidence,
                    )
                    for fix in review_output.code_fix_suggestions
                ]
            )

        # Commit immediately rather than relying on the request's final
        # commit-on-success in get_db(). A real Continuum call is expensive
        # (seconds to minutes) - if anything else in the same request fails
        # afterward, the whole shared session would roll back and silently
        # erase a review that had already succeeded.
        await self.reviews.session.commit()

        return review_output

    @staticmethod
    def _map_agent_failure(error_type: str | None, message: str | None) -> AppException:
        message = message or "AI review failed for an unknown reason"
        if error_type == "MalformedResponseError":
            return ValidationAppError(f"The AI returned a response that couldn't be parsed: {message}")
        if error_type == "ContinuumTimeoutError":
            return GatewayTimeoutError("The AI provider timed out. Please try again.")
        if error_type in ("ContinuumUnavailableError", "ContinuumConfigurationError"):
            return ServiceUnavailableError("The AI provider is currently unavailable.")
        return ServiceUnavailableError(f"AI review failed: {message}")
