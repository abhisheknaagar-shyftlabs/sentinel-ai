import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Incident(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """The canonical production object in Sentinel AI. Everything else -
    Docker monitoring, Root Cause Analysis, Safe Recovery - feeds into this
    rather than being queried directly by future alerts/dashboards."""

    __tablename__ = "incidents"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    root_cause_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    root_cause_confidence: Mapped[int | None] = mapped_column(Integer, nullable=True)

    recovery_recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    recovery_executed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    recovery_result: Mapped[str | None] = mapped_column(Text, nullable=True)

    affected_containers: Mapped[list["IncidentContainer"]] = relationship(
        back_populates="incident", cascade="all, delete-orphan"
    )
    events: Mapped[list["IncidentEvent"]] = relationship(
        back_populates="incident",
        cascade="all, delete-orphan",
        order_by="IncidentEvent.created_at",
    )


class IncidentContainer(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A snapshot of one container affected by an incident, taken at
    creation time - Docker state is live and can change/disappear, so this
    is the durable evidence record, not a live reference."""

    __tablename__ = "incident_containers"

    incident_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False
    )
    container_id: Mapped[str] = mapped_column(String(128), nullable=False)
    container_name: Mapped[str] = mapped_column(String(255), nullable=False)
    image: Mapped[str] = mapped_column(String(255), nullable=False)

    incident: Mapped["Incident"] = relationship(back_populates="affected_containers")


class IncidentEvent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """One entry in an incident's timeline. created_at (from TimestampMixin)
    is the event's own timestamp."""

    __tablename__ = "incident_events"

    incident_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    incident: Mapped["Incident"] = relationship(back_populates="events")
