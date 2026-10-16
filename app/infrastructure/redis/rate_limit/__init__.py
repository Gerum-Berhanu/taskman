"""Redis rate-limit algorithm helpers and name -> hit dispatch."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from redis.typing import EncodableT

from app.core.timeutils import utcnow
from app.infrastructure.redis.client import redis_client
from app.infrastructure.redis.lua_loader import LuaScriptName

__all__ = [
    "HITTERS",
    "HitFn",
    "LuaScriptName",
    "RateLimitResult",
    "hit_fixed_window_counter",
    "hit_leaky_bucket",
    "hit_sliding_window_counter",
    "hit_sliding_window_log",
    "hit_token_bucket",
]


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


from app.infrastructure.redis.rate_limit.fixed_window_counter import (  # noqa: E402
    hit_fixed_window_counter,
)
from app.infrastructure.redis.rate_limit.leaky_bucket import (  # noqa: E402
    hit_leaky_bucket,
)
from app.infrastructure.redis.rate_limit.sliding_window_counter import (  # noqa: E402
    hit_sliding_window_counter,
)
from app.infrastructure.redis.rate_limit.sliding_window_log import (  # noqa: E402
    hit_sliding_window_log,
)
from app.infrastructure.redis.rate_limit.token_bucket import (  # noqa: E402
    hit_token_bucket,
)

HITTERS: dict[LuaScriptName, HitFn] = {
    "fixed_window_counter": hit_fixed_window_counter,
    "leaky_bucket": hit_leaky_bucket,
    "sliding_window_counter": hit_sliding_window_counter,
    "sliding_window_log": hit_sliding_window_log,
    "token_bucket": hit_token_bucket,
}
