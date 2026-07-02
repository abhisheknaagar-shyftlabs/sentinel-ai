import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class TrackedRepository(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "repositories"
    __table_args__ = (
        UniqueConstraint("integration_id", "github_id", name="uq_repositories_integration_github_id"),
    )

    integration_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("integrations.id", ondelete="CASCADE"), nullable=False
    )
    github_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(500), nullable=False)
    private: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    default_branch: Mapped[str] = mapped_column(String(255), default="main", nullable=False)
    html_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    integration: Mapped["Integration"] = relationship(back_populates="repositories")
