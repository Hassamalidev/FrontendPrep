"""Timezone helpers.

``DateTime(timezone=True)`` round-trips as an aware datetime on Postgres but as
a naive one on SQLite, so any comparison or subtraction that mixes a stored
value with ``datetime.now(timezone.utc)`` raises on the test backend and works
in production -- the worst possible split. Everything that touches a stored
timestamp goes through ``as_utc`` first.
"""

from __future__ import annotations

from datetime import UTC, datetime


def utcnow() -> datetime:
    return datetime.now(UTC)


def as_utc(value: datetime | None) -> datetime | None:
    """Interpret a naive timestamp as UTC; pass an aware one through."""
    if value is None:
        return None
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def elapsed_seconds(start: datetime | None, end: datetime | None) -> int:
    """Whole seconds between two stored timestamps, safe against naive values."""
    start_utc, end_utc = as_utc(start), as_utc(end)
    if start_utc is None or end_utc is None:
        return 0
    return max(0, int((end_utc - start_utc).total_seconds()))
