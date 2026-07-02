from datetime import datetime, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_utc(dt: datetime) -> datetime:
    """SQLite (used in tests) round-trips timestamps as naive even though
    they were stored as UTC-aware; Postgres preserves tzinfo correctly. All
    datetimes in this app are UTC by convention, so a naive one is always
    safe to assume is UTC rather than a bug to crash on."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def format_relative_time(dt: datetime | None) -> str:
    """"12m ago" style, for frontend fields the contract lists as relative:
    timestamp, updatedAt, startedAt, lastSyncedAt."""
    if dt is None:
        return "never"
    delta = utc_now() - _ensure_utc(dt)
    seconds = max(int(delta.total_seconds()), 0)
    if seconds < 60:
        return f"{seconds} seconds ago"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h ago"
    days = hours // 24
    return f"{days}d ago"


def format_clock_time(dt: datetime | None) -> str:
    """"10:42:01" style, for log timestamps."""
    if dt is None:
        return "--:--:--"
    return dt.strftime("%H:%M:%S")


def format_duration_since(since: datetime | None) -> str:
    """"14d 6h" style, for container uptime."""
    if since is None:
        return "0d 0h"
    delta = utc_now() - _ensure_utc(since)
    days = max(delta.days, 0)
    hours = max(delta.seconds // 3600, 0)
    return f"{days}d {hours}h"


def format_plain_date(dt: datetime | None) -> str:
    """"2026-06-18" style, for technical debt detection dates."""
    if dt is None:
        return "unknown"
    return dt.date().isoformat()
