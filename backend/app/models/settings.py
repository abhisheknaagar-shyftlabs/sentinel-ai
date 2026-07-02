import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class UserSettings(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """One row per user. Scoped per-user rather than per-workspace since
    full workspace multi-tenancy isn't built out yet - User.workspace_id
    exists but is optional and unused for authorization anywhere today."""

    __tablename__ = "user_settings"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )

    # workspace section
    workspace_name: Mapped[str] = mapped_column(String(255), nullable=False, default="My Workspace")
    timezone: Mapped[str] = mapped_column(String(100), nullable=False, default="UTC")
    default_branch: Mapped[str] = mapped_column(String(255), nullable=False, default="main")

    # notifications section
    incident_alerts: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    pr_risk_alerts: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    weekly_digest: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    cost_alerts: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notification_email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # aiPreferences section
    auto_fix_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    auto_recovery_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    risk_sensitivity: Mapped[str] = mapped_column(String(20), nullable=False, default="balanced")
    min_confidence_threshold: Mapped[int] = mapped_column(Integer, nullable=False, default=80)
