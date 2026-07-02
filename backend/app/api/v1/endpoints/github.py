import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.continuum.client import ContinuumClient
from app.continuum.dependencies import get_continuum_client
from app.core.responses import success_envelope
from app.database.deps import get_db
from app.models.user import User
from app.repositories.ai_fix_repository import AIFixRepository
from app.repositories.ai_review_repository import AIReviewRepository
from app.schemas.integration import IntegrationCreate, IntegrationRead
from app.schemas.repository import RepositoryTrackRequest, TrackedRepositoryRead
from app.security.dependencies import get_current_user
from app.services.github_service import GitHubIntegrationService
from app.services.pr_review_service import PRReviewService

router = APIRouter(prefix="/github", tags=["github"])


def get_github_service(db: AsyncSession = Depends(get_db)) -> GitHubIntegrationService:
    return GitHubIntegrationService(db)


def get_pr_review_service(
    db: AsyncSession = Depends(get_db),
    continuum_client: ContinuumClient = Depends(get_continuum_client),
) -> PRReviewService:
    return PRReviewService(
        GitHubIntegrationService(db), continuum_client, AIReviewRepository(db), AIFixRepository(db)
    )


@router.post("/integrations", status_code=status.HTTP_201_CREATED)
async def connect_integration(
    payload: IntegrationCreate,
    current_user: User = Depends(get_current_user),
    service: GitHubIntegrationService = Depends(get_github_service),
):
    integration = await service.connect_integration(current_user.id, payload)
    return success_envelope(
        IntegrationRead.model_validate(integration).model_dump(mode="json"),
        "GitHub integration connected",
    )


@router.get("/integrations")
async def list_integrations(
    current_user: User = Depends(get_current_user),
    service: GitHubIntegrationService = Depends(get_github_service),
):
    integrations = await service.list_integrations(current_user.id)
    return success_envelope([IntegrationRead.model_validate(i).model_dump(mode="json") for i in integrations])


@router.delete("/integrations/{integration_id}")
async def disconnect_integration(
    integration_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: GitHubIntegrationService = Depends(get_github_service),
):
    await service.disconnect_integration(current_user.id, integration_id)
    return success_envelope(None, "GitHub integration disconnected")


@router.get("/integrations/{integration_id}/repositories")
async def list_available_repositories(
    integration_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: GitHubIntegrationService = Depends(get_github_service),
):
    repos = await service.list_available_repositories(current_user.id, integration_id)
    return success_envelope([r.model_dump(mode="json") for r in repos])


@router.post("/integrations/{integration_id}/repositories", status_code=status.HTTP_201_CREATED)
async def track_repository(
    integration_id: uuid.UUID,
    payload: RepositoryTrackRequest,
    current_user: User = Depends(get_current_user),
    service: GitHubIntegrationService = Depends(get_github_service),
):
    tracked = await service.track_repository(current_user.id, integration_id, payload)
    return success_envelope(
        TrackedRepositoryRead.model_validate(tracked).model_dump(mode="json"),
        "Repository is now tracked",
    )


@router.get("/repositories")
async def list_tracked_repositories(
    current_user: User = Depends(get_current_user),
    service: GitHubIntegrationService = Depends(get_github_service),
):
    repos = await service.list_tracked_repositories(current_user.id)
    return success_envelope([TrackedRepositoryRead.model_validate(r).model_dump(mode="json") for r in repos])


@router.get("/repositories/{repository_id}/pulls")
async def list_pull_requests(
    repository_id: uuid.UUID,
    state: str = Query("open", pattern="^(open|closed|all)$"),
    current_user: User = Depends(get_current_user),
    service: GitHubIntegrationService = Depends(get_github_service),
):
    prs = await service.list_pull_requests(current_user.id, repository_id, state)
    return success_envelope([pr.model_dump(mode="json") for pr in prs])


@router.get("/repositories/{repository_id}/pulls/{pr_number}")
async def get_pull_request(
    repository_id: uuid.UUID,
    pr_number: int,
    current_user: User = Depends(get_current_user),
    service: GitHubIntegrationService = Depends(get_github_service),
):
    pr = await service.get_pull_request(current_user.id, repository_id, pr_number)
    return success_envelope(pr.model_dump(mode="json"))


@router.get("/repositories/{repository_id}/pulls/{pr_number}/diff")
async def get_pull_request_diff(
    repository_id: uuid.UUID,
    pr_number: int,
    current_user: User = Depends(get_current_user),
    service: GitHubIntegrationService = Depends(get_github_service),
):
    diff = await service.get_pull_request_diff(current_user.id, repository_id, pr_number)
    return success_envelope({"diff": diff})


@router.get("/repositories/{repository_id}/pulls/{pr_number}/files")
async def list_pull_request_files(
    repository_id: uuid.UUID,
    pr_number: int,
    current_user: User = Depends(get_current_user),
    service: GitHubIntegrationService = Depends(get_github_service),
):
    files = await service.list_pull_request_files(current_user.id, repository_id, pr_number)
    return success_envelope([f.model_dump(mode="json") for f in files])


@router.get("/repositories/{repository_id}/pulls/{pr_number}/commits")
async def list_pull_request_commits(
    repository_id: uuid.UUID,
    pr_number: int,
    current_user: User = Depends(get_current_user),
    service: GitHubIntegrationService = Depends(get_github_service),
):
    commits = await service.list_pull_request_commits(current_user.id, repository_id, pr_number)
    return success_envelope([c.model_dump(mode="json") for c in commits])


@router.post(
    "/repositories/{repository_id}/pulls/{pr_number}/review",
    summary="Run an AI-powered senior-engineer review of a pull request",
    description=(
        "Fetches the pull request's latest metadata, diff, changed files, and commits from GitHub, "
        "runs them through the Continuum-orchestrated PR Review agent, persists a summary of the "
        "result, and returns the full structured review (executive summary, risk score, deployment "
        "confidence, technical debt, findings by category, breaking-change detection, suggested "
        "fixes, and an approve / approve-with-changes / request-changes recommendation)."
    ),
)
async def review_pull_request(
    repository_id: uuid.UUID,
    pr_number: int,
    current_user: User = Depends(get_current_user),
    service: PRReviewService = Depends(get_pr_review_service),
):
    result = await service.review_pull_request(current_user.id, repository_id, pr_number)
    return success_envelope(result.model_dump(mode="json"), "PR review completed")
