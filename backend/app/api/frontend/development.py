import uuid
from dataclasses import dataclass
from datetime import timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from pydantic import Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.development.schemas import ChangedFileSummary, CompareReviewOutput, PRReviewInput, Recommendation
from app.continuum.client import ContinuumClient
from app.continuum.dependencies import get_continuum_client
from app.continuum.registry import get_global_registry
from app.core.exceptions import AppException, NotFoundError
from app.core.jobs import JobStatus, create_job, get_job, set_job_completed, set_job_failed, set_job_running
from app.core.logging import get_logger
from app.database.deps import get_db
from app.database.session import AsyncSessionLocal
from app.models.user import User
from app.repositories.ai_fix_repository import AIFixRepository
from app.repositories.ai_review_repository import AIReviewRepository
from app.repositories.tracked_repository_repository import TrackedRepositoryRepository
from app.schemas.camel import CamelModel
from app.security.dependencies import get_current_user
from app.services.github_service import GitHubIntegrationService
from app.services.pr_review_service import PRReviewService
from app.services.technical_debt_service import TechnicalDebtService
from app.utils.time import format_relative_time, utc_now

router = APIRouter(prefix="/development-intelligence", tags=["frontend-development"])
logger = get_logger(__name__)

_MAX_PRS_PER_SUMMARY = 10
_REVIEW_FRESHNESS = timedelta(hours=24)


class Trend(CamelModel):
    direction: str
    change_percent: float
    is_positive: bool


class DevStats(CamelModel):
    # to_camel doesn't know "PR" is an acronym (open_prs -> openPrs, not
    # openPRs) - explicit aliases override the generator for these three.
    open_prs: int = Field(serialization_alias="openPRs")
    open_prs_trend: Trend = Field(serialization_alias="openPRsTrend")
    high_risk_prs: int = Field(serialization_alias="highRiskPRs")
    avg_deployment_confidence: int
    avg_deployment_confidence_trend: Trend
    technical_debt_hours: int
    technical_debt_trend: Trend


class PullRequestItem(CamelModel):
    id: str
    number: int
    title: str
    author: str
    branch: str
    base_branch: str
    risk: str
    deployment_confidence: int
    files_changed: int
    lines_added: int
    lines_removed: int
    status: str
    updated_at: str
    html_url: str
    # Extra fields beyond the original contract - drive the frontend's
    # on-demand review button instead of running AI review for every PR.
    reviewed: bool = True
    repository_id: str


class OnDemandReviewResult(CamelModel):
    number: int
    risk: str
    deployment_confidence: int
    files_changed: int
    lines_added: int
    lines_removed: int
    reviewed: bool = True


class TechnicalDebtItemResponse(CamelModel):
    id: str
    module: str
    description: str
    severity: str
    estimated_hours: int
    detected_at: str


class AiFixItem(CamelModel):
    id: str
    pr_number: int
    title: str
    description: str
    status: str
    confidence: int


class DevSummaryResponse(CamelModel):
    stats: DevStats
    pull_requests: list[PullRequestItem]
    technical_debt: list[TechnicalDebtItemResponse]
    ai_fixes: list[AiFixItem]


class BranchItem(CamelModel):
    name: str
    last_commit: str
    author: str
    is_protected: bool | None = None


class ChangedFileItem(CamelModel):
    path: str
    status: str
    additions: int
    deletions: int
    risk: str


class CompareResponse(CamelModel):
    base: str
    head: str
    identical: bool
    commits_ahead: int
    commits_behind: int
    files_changed: int
    additions: int
    deletions: int
    risk: str
    deployment_confidence: int
    merge_score: int
    recommendation: str
    summary: str
    gains: list[str]
    risks: list[str]
    changed_files: list[ChangedFileItem]


@dataclass
class _ReviewSummary:
    risk: str
    deployment_confidence: int


_RISK_BUCKETS = (
    (85, "critical"),
    (60, "high"),
    (30, "medium"),
)


def _risk_level_from_score(score: int) -> str:
    for threshold, level in _RISK_BUCKETS:
        if score >= threshold:
            return level
    return "low"


def get_github_service(db: AsyncSession = Depends(get_db)) -> GitHubIntegrationService:
    return GitHubIntegrationService(db)


def get_pr_review_service(
    db: AsyncSession = Depends(get_db),
    continuum_client: ContinuumClient = Depends(get_continuum_client),
) -> PRReviewService:
    return PRReviewService(
        GitHubIntegrationService(db), continuum_client, AIReviewRepository(db), AIFixRepository(db)
    )


def get_technical_debt_service(db: AsyncSession = Depends(get_db)) -> TechnicalDebtService:
    return TechnicalDebtService(AIReviewRepository(db), TrackedRepositoryRepository(db))


async def _find_fresh_review(ai_reviews: AIReviewRepository, repository_id, pr_number: int):
    existing = await ai_reviews.list_for_repository(repository_id)
    return next(
        (
            r
            for r in existing
            if r.pull_request_number == pr_number and utc_now() - _as_utc(r.review_timestamp) < _REVIEW_FRESHNESS
        ),
        None,
    )


async def _get_cached_review_only(
    ai_reviews: AIReviewRepository, repository_id, pr_number: int
) -> _ReviewSummary | None:
    """Never triggers a real Continuum call - used for every PR in the
    summary list except the single most-recent one, so opening the page
    doesn't burn a review on every PR whether anyone asked for it or not."""
    fresh = await _find_fresh_review(ai_reviews, repository_id, pr_number)
    if fresh is None:
        return None
    return _ReviewSummary(risk=_risk_level_from_score(fresh.risk_score), deployment_confidence=fresh.deployment_confidence)


async def _get_or_run_review(
    pr_review_service: PRReviewService,
    ai_reviews: AIReviewRepository,
    user_id,
    repository_id,
    pr_number: int,
) -> _ReviewSummary:
    """Uses a fresh persisted review if one exists; otherwise runs a real
    Continuum PR review. Reserved for the single most-recently-updated PR on
    the summary page and for the explicit on-demand review endpoint - never
    called in a loop over every PR, since each call can be a real,
    potentially multi-minute Continuum request."""
    fresh = await _find_fresh_review(ai_reviews, repository_id, pr_number)
    if fresh is not None:
        return _ReviewSummary(risk=_risk_level_from_score(fresh.risk_score), deployment_confidence=fresh.deployment_confidence)

    try:
        output = await pr_review_service.review_pull_request(user_id, repository_id, pr_number)
    except AppException as exc:
        logger.warning(
            "pr_list_review_failed",
            extra={"repository_id": str(repository_id), "pr_number": pr_number, "error": str(exc)},
        )
        return _ReviewSummary(risk="medium", deployment_confidence=50)

    return _ReviewSummary(
        risk=_risk_level_from_score(output.risk_assessment.score),
        deployment_confidence=output.deployment_confidence.score,
    )


def _as_utc(dt):
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


async def _get_primary_tracked_repository(github_service: GitHubIntegrationService, user_id):
    """The contract has no repository selector for branches/compare - pick
    the user's first tracked repository as the implicit default."""
    tracked = await github_service.list_tracked_repositories(user_id)
    if not tracked:
        raise NotFoundError("No tracked GitHub repository - connect and track one first")
    return tracked[0]


@router.get("/summary", response_model=DevSummaryResponse)
async def get_summary(
    current_user: User = Depends(get_current_user),
    github_service: GitHubIntegrationService = Depends(get_github_service),
    technical_debt_service: TechnicalDebtService = Depends(get_technical_debt_service),
    db: AsyncSession = Depends(get_db),
):
    ai_reviews = AIReviewRepository(db)
    ai_fixes = AIFixRepository(db)

    tracked_repos = await github_service.list_tracked_repositories(current_user.id)

    raw_prs = []
    for repo in tracked_repos:
        prs = await github_service.list_pull_requests(current_user.id, repo.id, state="open")
        raw_prs.extend((repo, pr) for pr in prs)

    raw_prs.sort(key=lambda pair: pair[1].updated_at, reverse=True)
    truncated = len(raw_prs) > _MAX_PRS_PER_SUMMARY
    if truncated:
        logger.info(
            "dev_summary_pr_list_truncated",
            extra={"total_open_prs": len(raw_prs), "shown": _MAX_PRS_PER_SUMMARY},
        )
    raw_prs = raw_prs[:_MAX_PRS_PER_SUMMARY]

    pull_requests: list[PullRequestItem] = []
    for repo, pr in raw_prs:
        files = await github_service.list_pull_request_files(current_user.id, repo.id, pr.number)

        # Never trigger a real Continuum call from the summary load, for any
        # PR - only a persisted review counts as "reviewed" here. Running a
        # fresh review is exclusively the on-demand endpoint's job, fired by
        # an explicit user action (the "Run review" button).
        cached = await _get_cached_review_only(ai_reviews, repo.id, pr.number)
        reviewed = cached is not None
        review = cached or _ReviewSummary(risk="low", deployment_confidence=100)

        pull_requests.append(
            PullRequestItem(
                id=f"pr-{pr.number}",
                number=pr.number,
                title=pr.title,
                author=pr.user_login,
                branch=pr.head_branch,
                base_branch=pr.base_branch,
                risk=review.risk,
                deployment_confidence=review.deployment_confidence,
                files_changed=len(files),
                lines_added=sum(f.additions for f in files),
                lines_removed=sum(f.deletions for f in files),
                status="draft" if pr.draft else "open",
                updated_at=format_relative_time(pr.updated_at),
                html_url=pr.html_url,
                reviewed=reviewed,
                repository_id=str(repo.id),
            )
        )

    reviewed_prs = [pr for pr in pull_requests if pr.reviewed]
    high_risk_count = sum(1 for pr in reviewed_prs if pr.risk in ("high", "critical"))
    avg_confidence = (
        round(sum(pr.deployment_confidence for pr in reviewed_prs) / len(reviewed_prs))
        if reviewed_prs
        else 100
    )

    debt_items = await technical_debt_service.list_technical_debt(current_user.id)
    technical_debt_hours = sum(item.estimated_hours for item in debt_items)

    recent_fixes = await ai_fixes.list_recent_for_user(current_user.id, limit=20)

    zero_trend = Trend(direction="flat", change_percent=0, is_positive=True)

    return DevSummaryResponse(
        stats=DevStats(
            open_prs=len(pull_requests),
            open_prs_trend=zero_trend,
            high_risk_prs=high_risk_count,
            avg_deployment_confidence=avg_confidence,
            avg_deployment_confidence_trend=zero_trend,
            technical_debt_hours=technical_debt_hours,
            technical_debt_trend=zero_trend,
        ),
        pull_requests=pull_requests,
        technical_debt=[
            TechnicalDebtItemResponse(
                id=str(item.id),
                module=item.module,
                description=item.description,
                severity=item.severity.value,
                estimated_hours=item.estimated_hours,
                detected_at=item.detected_at,
            )
            for item in debt_items
        ],
        ai_fixes=[
            AiFixItem(
                id=str(fix.id),
                pr_number=fix.pull_request_number,
                title=fix.description,
                description=f"Suggested for {fix.file}",
                status=fix.status,
                confidence=fix.confidence,
            )
            for fix in recent_fixes
        ],
    )


@router.post("/repositories/{repository_id}/pulls/{pr_number}/review", response_model=OnDemandReviewResult)
async def review_pull_request_on_demand(
    repository_id: uuid.UUID,
    pr_number: int,
    current_user: User = Depends(get_current_user),
    github_service: GitHubIntegrationService = Depends(get_github_service),
    pr_review_service: PRReviewService = Depends(get_pr_review_service),
    db: AsyncSession = Depends(get_db),
):
    """The explicit, user-triggered counterpart to get_summary()'s
    auto-reviewed-top-PR-only behavior - this is the only way the other PRs
    in the list ever get a real Continuum review."""
    ai_reviews = AIReviewRepository(db)
    files = await github_service.list_pull_request_files(current_user.id, repository_id, pr_number)
    review = await _get_or_run_review(pr_review_service, ai_reviews, current_user.id, repository_id, pr_number)
    return OnDemandReviewResult(
        number=pr_number,
        risk=review.risk,
        deployment_confidence=review.deployment_confidence,
        files_changed=len(files),
        lines_added=sum(f.additions for f in files),
        lines_removed=sum(f.deletions for f in files),
    )


@router.get("/branches", response_model=list[BranchItem])
async def get_branches(
    current_user: User = Depends(get_current_user),
    github_service: GitHubIntegrationService = Depends(get_github_service),
):
    repo = await _get_primary_tracked_repository(github_service, current_user.id)
    branches = await github_service.list_branches(current_user.id, repo.id)
    return [
        BranchItem(
            name=b.name,
            last_commit=format_relative_time(b.last_commit_at),
            author=b.last_commit_author or "unknown",
            is_protected=b.protected,
        )
        for b in branches
    ]


def _synthesize_diff(files: list) -> str:
    """GitHub's compare API doesn't return one unified diff blob the way the
    single-PR diff endpoint does - reconstruct an equivalent from each
    file's own patch, which we already have."""
    parts = []
    for f in files:
        if f.patch:
            parts.append(f"diff --git a/{f.filename} b/{f.filename}\n{f.patch}")
    return "\n".join(parts)


async def _compute_compare(
    db: AsyncSession,
    github_service: GitHubIntegrationService,
    continuum_client: ContinuumClient,
    user_id: uuid.UUID,
    base: str,
    head: str,
) -> CompareResponse:
    """The actual comparison work, independent of how it's invoked (job
    background task or, in principle, a direct call) - no FastAPI Depends()
    here, just plain arguments, so it can run outside a request's own DI
    scope (see _run_compare_job)."""
    if base == head:
        return CompareResponse(
            base=base,
            head=head,
            identical=True,
            commits_ahead=0,
            commits_behind=0,
            files_changed=0,
            additions=0,
            deletions=0,
            risk="low",
            deployment_confidence=100,
            merge_score=100,
            recommendation="merge",
            summary="Base and head are the same branch - nothing to compare.",
            gains=[],
            risks=[],
            changed_files=[],
        )

    repo = await _get_primary_tracked_repository(github_service, user_id)
    comparison = await github_service.compare_branches(user_id, repo.id, base, head)
    files_changed = len(comparison.files)

    agent_input = PRReviewInput(
        repository_full_name=repo.full_name,
        pr_number=0,
        title=f"Compare {head} into {base}",
        description=f"{comparison.total_commits} commit(s), {comparison.ahead_by} ahead / {comparison.behind_by} behind {base}.",
        base_branch=base,
        head_branch=head,
        diff=_synthesize_diff(comparison.files),
        changed_files=[
            ChangedFileSummary(
                filename=f.filename, status=f.status, additions=f.additions, deletions=f.deletions, patch=f.patch
            )
            for f in comparison.files
        ],
    )
    result = await continuum_client.run_agent("pr_compare_review", agent_input)
    if not result.success:
        raise PRReviewService._map_agent_failure(result.error_type, result.error)
    output = result.data
    assert isinstance(output, CompareReviewOutput)

    risk = _risk_level_from_score(output.risk_score)
    deployment_confidence = output.deployment_confidence
    merge_score = deployment_confidence
    recommendation = (
        "merge"
        if output.recommendation == Recommendation.APPROVE
        else "hold"
        if output.recommendation == Recommendation.REQUEST_CHANGES
        else "caution"
    )

    risks = [f"{finding.title}: {finding.description}" for finding in output.findings] or (
        [f"Touches {files_changed} files with {comparison.additions + comparison.deletions} changed lines"]
        if files_changed
        else []
    )
    gains = [f"Incorporates {comparison.ahead_by} commit(s) not yet on {base}"] if comparison.ahead_by else []

    return CompareResponse(
        base=base,
        head=head,
        identical=False,
        commits_ahead=comparison.ahead_by,
        commits_behind=comparison.behind_by,
        files_changed=files_changed,
        additions=comparison.additions,
        deletions=comparison.deletions,
        risk=risk,
        deployment_confidence=deployment_confidence,
        merge_score=merge_score,
        recommendation=recommendation,
        summary=output.summary,
        gains=gains,
        risks=risks,
        changed_files=[
            ChangedFileItem(
                path=f.filename,
                status=f.status,
                additions=f.additions,
                deletions=f.deletions,
                risk="high" if f.additions + f.deletions > 100 else "low",
            )
            for f in comparison.files
        ],
    )


async def _run_compare_job(job_id: str, user_id: uuid.UUID, base: str, head: str) -> None:
    """Runs after the response is already sent (FastAPI BackgroundTasks), so
    none of the original request's Depends()-injected db/services are still
    valid by the time this executes - build fresh ones instead. This is the
    whole point: a real AI call can take up to ~250s (see CLAUDE.md), and no
    production load balancer/proxy will hold a single HTTP request open
    that long, regardless of our own app-level timeout settings."""
    await set_job_running(job_id)
    try:
        async with AsyncSessionLocal() as db:
            github_service = GitHubIntegrationService(db)
            continuum_client = ContinuumClient(registry=get_global_registry())
            response = await _compute_compare(db, github_service, continuum_client, user_id, base, head)
            await db.commit()
        await set_job_completed(job_id, response.model_dump(by_alias=True))
    except AppException as exc:
        logger.warning("compare_job_failed", extra={"job_id": job_id, "error": exc.message})
        await set_job_failed(job_id, exc.message, exc.code)
    except Exception as exc:  # noqa: BLE001 - any unexpected failure still resolves the job, never hangs it
        logger.warning("compare_job_failed", extra={"job_id": job_id, "error": str(exc)})
        await set_job_failed(job_id, str(exc))


class CompareJobStartResponse(CamelModel):
    job_id: str
    status: str


class CompareJobStatusResponse(CamelModel):
    job_id: str
    status: str
    result: CompareResponse | None = None
    error: str | None = None


@router.post("/compare/jobs", response_model=CompareJobStartResponse, status_code=202)
async def start_compare_job(
    background_tasks: BackgroundTasks,
    base: str = Query(...),
    head: str = Query(...),
    current_user: User = Depends(get_current_user),
):
    job_id = await create_job()
    background_tasks.add_task(_run_compare_job, job_id, current_user.id, base, head)
    return CompareJobStartResponse(job_id=job_id, status=JobStatus.PENDING.value)


@router.get("/compare/jobs/{job_id}", response_model=CompareJobStatusResponse)
async def get_compare_job(job_id: str, current_user: User = Depends(get_current_user)):
    job = await get_job(job_id)
    if job is None:
        raise NotFoundError("Job not found or expired")
    return CompareJobStatusResponse(
        job_id=job.id,
        status=job.status.value,
        result=CompareResponse.model_validate(job.result) if job.result else None,
        error=job.error,
    )
