import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AIFix(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """One AI-suggested code fix from a PR review, persisted so it can be
    listed later (frontend's "AI fixes" panel) without re-running review.
    Populated as a side effect of PRReviewService.review_pull_request() -
    never a separate AI call."""

    __tablename__ = "ai_fixes"

    repository_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False
    )
    pull_request_number: Mapped[int] = mapped_column(Integer, nullable=False)
    file: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_patch: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="suggested")
    confidence: Mapped[int] = mapped_column(Integer, nullable=False)
