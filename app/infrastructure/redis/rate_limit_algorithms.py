"""Redis rate-limit algorithm helpers and name -> hit dispatch."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from uuid import uuid4

from redis.typing import EncodableT

from app.core.timeutils import utcnow
from app.infrastructure.redis.client import redis_client
from app.infrastructure.redis.lua import LuaScriptName


@dataclass(frozen=True)
class RateLimitResult:
    """Outcome of one rate-limit check.

    retry_after_ms is 0 when allowed; otherwise milliseconds until a retry may succeed 
    (same meaning for every algorithm).
    """

    allowed: bool
    retry_after_ms: int


HitFn = Callable[..., Awaitable[RateLimitResult]]


async def _hit(
    script_name: LuaScriptName,
    scope: str,
    identity: str,
    limit: int,
    window_seconds: int,
    *extra_args: EncodableT,
) -> RateLimitResult:
    prefix = "rl"
    key = f"{prefix}:{script_name}:{scope}:{identity}"
    now_ms = int(utcnow().timestamp() * 1000)
    window_ms = window_seconds * 1000
    allowed_flag, retry_after_ms = await redis_client.scripts[script_name](
        keys=[key],
        args=[now_ms, window_ms, limit, *extra_args],
    )
    return RateLimitResult(
        allowed=bool(int(allowed_flag)),
        retry_after_ms=int(retry_after_ms),
    )


async def hit_fixed_window_counter(
    scope: str, identity: str, limit: int, window_seconds: int
) -> RateLimitResult:
    return await _hit(
        "fixed_window_counter", scope, identity, limit, window_seconds
    )


async def hit_leaky_bucket(
    scope: str, identity: str, limit: int, window_seconds: int
) -> RateLimitResult:
    return await _hit(
        "leaky_bucket", scope, identity, limit, window_seconds
    )


async def hit_sliding_window_counter(
    scope: str, identity: str, limit: int, window_seconds: int
) -> RateLimitResult:
    """Approximate sliding-window counter hit."""
    return await _hit(
        "sliding_window_counter", scope, identity, limit, window_seconds
    )


async def hit_sliding_window_log(
    scope: str, identity: str, limit: int, window_seconds: int
) -> RateLimitResult:
    """Exact ZSET sliding-window hit."""
    now_ms = int(utcnow().timestamp() * 1000)
    member = f"{now_ms}:{uuid4()}"
    return await _hit(
        "sliding_window_log", scope, identity, limit, window_seconds, member
    )


async def hit_token_bucket(
    scope: str, identity: str, limit: int, window_seconds: int
) -> RateLimitResult:
    return await _hit(
        "token_bucket", scope, identity, limit, window_seconds
    )


HITTERS: dict[LuaScriptName, HitFn] = {
    "fixed_window_counter": hit_fixed_window_counter,
    "leaky_bucket": hit_leaky_bucket,
    "sliding_window_counter": hit_sliding_window_counter,
    "sliding_window_log": hit_sliding_window_log,
    "token_bucket": hit_token_bucket,
}
