"""Redis rate-limit algorithm helpers and name -> hit dispatch."""

from app.infrastructure.redis.lua_loader import LuaScriptName
from app.infrastructure.redis.rate_limit.algorithm import (
    RateLimitAlgorithm,
    RateLimitResult,
    SlidingWindowLog,
)

__all__ = [
    "HITTERS",
    "LuaScriptName",
    "RateLimitResult",
]

HITTERS: dict[LuaScriptName, RateLimitAlgorithm] = {
    "fixed_window_counter": RateLimitAlgorithm("fixed_window_counter"),
    "leaky_bucket": RateLimitAlgorithm("leaky_bucket"),
    "sliding_window_counter": RateLimitAlgorithm("sliding_window_counter"),
    "sliding_window_log": SlidingWindowLog(),
    "token_bucket": RateLimitAlgorithm("token_bucket"),
}
