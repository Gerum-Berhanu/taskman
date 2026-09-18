from datetime import datetime, timezone

from sqlalchemy import DateTime
from sqlalchemy.types import TypeDecorator


def utcnow() -> datetime:
    """Return the current time as timezone-aware UTC."""
    return datetime.now(timezone.utc)


def ensure_utc(value: datetime) -> datetime:
    """Normalize datetimes for comparison (treat naive values as UTC)."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class UTCDateTime(TypeDecorator):
    """Store and load timezone-aware UTC datetimes (SQLite-safe)."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(
        self, value: datetime | None, dialect
    ) -> datetime | None:
        if value is None:
            return None
        return ensure_utc(value)

    def process_result_value(
        self, value: datetime | None, dialect
    ) -> datetime | None:
        if value is None:
            return None
        return ensure_utc(value)
