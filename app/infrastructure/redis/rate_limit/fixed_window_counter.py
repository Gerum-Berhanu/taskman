"""Fixed-window counter rate-limit hit."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.infrastructure.redis.rate_limit import RateLimitResult


async def hit_fixed_window_counter(
    scope: str, identity: str, limit: int, window_seconds: int
) -> "RateLimitResult":
    from app.infrastructure.redis.rate_limit import _hit

    return await _hit(
        "fixed_window_counter", scope, identity, limit, window_seconds
    )
