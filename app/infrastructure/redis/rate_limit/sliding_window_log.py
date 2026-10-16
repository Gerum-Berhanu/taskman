"""Exact ZSET sliding-window rate-limit hit."""

from typing import TYPE_CHECKING
from uuid import uuid4

from app.core.timeutils import utcnow

if TYPE_CHECKING:
    from app.infrastructure.redis.rate_limit import RateLimitResult


async def hit_sliding_window_log(
    scope: str, identity: str, limit: int, window_seconds: int
) -> "RateLimitResult":
    """Exact ZSET sliding-window hit."""
    from app.infrastructure.redis.rate_limit import _hit

    now_ms = int(utcnow().timestamp() * 1000)
    member = f"{now_ms}:{uuid4()}"
    return await _hit(
        "sliding_window_log", scope, identity, limit, window_seconds, member
    )
