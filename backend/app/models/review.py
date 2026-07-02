import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.utils.time import utc_now


class AIReview(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A persisted record of one AI PR review. Never stores the raw diff or
    any other GitHub content — that's always re-fetched live. This table
    exists purely for historical review tracking."""

    __tablename__ = "ai_reviews"

    repository_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False
    )
    pull_request_number: Mapped[int] = mapped_column(Integer, nullable=False)
    review_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False)
    deployment_confidence: Mapped[int] = mapped_column(Integer, nullable=False)
    recommendation: Mapped[str] = mapped_column(String(50), nullable=False)
    technical_debt_summary: Mapped[str] = mapped_column(Text, nullable=False)
