from datetime import timedelta

from app.utils.time import (
    format_clock_time,
    format_duration_since,
    format_plain_date,
    format_relative_time,
    utc_now,
)


def test_format_relative_time_buckets():
    now = utc_now()
    assert format_relative_time(now - timedelta(seconds=30)) == "30 seconds ago"
    assert format_relative_time(now - timedelta(minutes=12)) == "12m ago"
    assert format_relative_time(now - timedelta(hours=2)) == "2h ago"
    assert format_relative_time(now - timedelta(days=3)) == "3d ago"


def test_format_relative_time_none():
    assert format_relative_time(None) == "never"


def test_format_clock_time():
    now = utc_now().replace(hour=10, minute=42, second=1, microsecond=0)
    assert format_clock_time(now) == "10:42:01"


def test_format_duration_since():
    now = utc_now()
    assert format_duration_since(now - timedelta(days=14, hours=6)) == "14d 6h"


def test_format_plain_date():
    now = utc_now()
    assert format_plain_date(now) == now.date().isoformat()


def test_format_none_values():
    assert format_clock_time(None) == "--:--:--"
    assert format_duration_since(None) == "0d 0h"
    assert format_plain_date(None) == "unknown"
