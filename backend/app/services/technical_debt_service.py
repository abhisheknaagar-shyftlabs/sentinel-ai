import uuid

from pydantic import BaseModel

from app.agents.development.schemas import RiskLevel
from app.repositories.ai_review_repository import AIReviewRepository
from app.repositories.tracked_repository_repository import TrackedRepositoryRepository
from app.utils.time import format_plain_date

_TRIVIAL_SUMMARIES = {
    "",
    "none.",
    "none",
    "none introduced.",
    "no technical debt introduced.",
    "no technical debt.",
}


class TechnicalDebtItem(BaseModel):
    id: uuid.UUID
    module: str
    description: str
    severity: RiskLevel
    estimated_hours: int
    detected_at: str


def _severity_from_risk_score(risk_score: int) -> RiskLevel:
    if risk_score >= 85:
        return RiskLevel.CRITICAL
    if risk_score >= 60:
        return RiskLevel.HIGH
    if risk_score >= 30:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def _estimated_hours_from_risk_score(risk_score: int) -> int:
    # A heuristic derived from the review's own real risk score - not a
    # precise estimate, but not fabricated from nothing either.
    return max(1, round(risk_score / 100 * 40))


class TechnicalDebtService:
    """Derives a technical debt list from real PR review output -
    specifically AIReview.technical_debt_summary, which the existing
    pr_review Continuum agent already generates on every review. This is a
    transformation of real, already-generated AI output, not a new
    detection capability or a second AI call."""

    def __init__(self, reviews: AIReviewRepository, tracked_repos: TrackedRepositoryRepository) -> None:
        self.reviews = reviews
        self.tracked_repos = tracked_repos

    async def list_technical_debt(self, user_id: uuid.UUID, limit: int = 20) -> list[TechnicalDebtItem]:
        reviews = await self.reviews.list_recent_for_user(user_id, limit=200)
        repo_names: dict[uuid.UUID, str] = {}

        items: list[TechnicalDebtItem] = []
        for review in reviews:
            summary = (review.technical_debt_summary or "").strip()
            if summary.lower() in _TRIVIAL_SUMMARIES:
                continue

            if review.repository_id not in repo_names:
                repo = await self.tracked_repos.get_by_id(review.repository_id)
                repo_names[review.repository_id] = repo.full_name if repo else "unknown"

            items.append(
                TechnicalDebtItem(
                    id=review.id,
                    module=repo_names[review.repository_id],
                    description=summary,
                    severity=_severity_from_risk_score(review.risk_score),
                    estimated_hours=_estimated_hours_from_risk_score(review.risk_score),
                    detected_at=format_plain_date(review.review_timestamp),
                )
            )
            if len(items) >= limit:
                break

        return items
