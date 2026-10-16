"""Token-bucket rate-limit hit."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.infrastructure.redis.rate_limit import RateLimitResult


async def hit_token_bucket(
    scope: str, identity: str, limit: int, window_seconds: int
) -> "RateLimitResult":
    from app.infrastructure.redis.rate_limit import _hit

    return await _hit(
        "token_bucket", scope, identity, limit, window_seconds
    )
