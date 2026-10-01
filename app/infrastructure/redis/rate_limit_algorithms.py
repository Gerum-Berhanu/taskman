"""Redis sliding-window rate-limit algorithm helpers."""

from dataclasses import dataclass
from uuid import uuid4

from redis.typing import EncodableT

from app.core.timeutils import utcnow
from app.infrastructure.redis.client import redis_client
from app.infrastructure.redis.lua import LuaScriptName


@dataclass(frozen=True)
class RateLimitResult:
    """Outcome of one sliding-window rate-limit check."""
    allowed: bool
    count: int
    limit: int


async def _hit(
    script_name: LuaScriptName,
    policy: str,
    identity: str,
    limit: int,
    window_seconds: int,
    *extra_args: EncodableT,
) -> RateLimitResult:
    prefix = f"rl_{script_name}"
    key = f"{prefix}:{policy}:{identity}"
    now_ms = int(utcnow().timestamp() * 1000)
    window_ms = window_seconds * 1000
    allowed_flag, count = await redis_client.scripts[script_name](
        keys=[key],
        args=[now_ms, window_ms, limit, *extra_args],
    )
    return RateLimitResult(
        allowed=bool(int(allowed_flag)),
        count=int(count),
        limit=limit,
    )


async def hit_sliding_window_counter(
    policy: str, identity: str, limit: int, window_seconds: int
) -> RateLimitResult:
    """Approximate sliding-window counter hit (used by HTTP rate-limit middleware)."""
    return await _hit(
        "sliding_window_counter", policy, identity, limit, window_seconds
    )


async def hit_sliding_window_log(
    policy: str, identity: str, limit: int, window_seconds: int
) -> RateLimitResult:
    """Exact ZSET sliding-window hit (alternate; middleware uses the counter)."""
    now_ms = int(utcnow().timestamp() * 1000)
    member = f"{now_ms}:{uuid4()}"
    return await _hit(
        "sliding_window_log", policy, identity, limit, window_seconds, member
    )
    
