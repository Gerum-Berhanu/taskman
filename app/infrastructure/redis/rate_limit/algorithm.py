"""Rate-limit algorithm strategies (Redis Lua hit + result type)."""

from dataclasses import dataclass
from typing import TypedDict, Unpack
from uuid import uuid4

from redis.typing import EncodableT

from app.core.timeutils import utcnow
from app.infrastructure.redis.client import redis_client
from app.infrastructure.redis.lua_loader import LuaScriptName


@dataclass(frozen=True)
class RateLimitResult:
    """Outcome of one rate-limit check. retry_after_ms is 0 when allowed"""

    allowed: bool
    retry_after_ms: int


class HitKwargs(TypedDict):
    scope: str
    identity: str
    limit: int
    window_seconds: int


class ExtraArgvKwargs(TypedDict):
    now_ms: int
    # add shared fields here later if needed


class RateLimitAlgorithm:
    def __init__(self, script_name: LuaScriptName) -> None:
        self.script_name: LuaScriptName = script_name

    def extra_argv(self, **kwargs: Unpack[ExtraArgvKwargs]) -> tuple[EncodableT, ...]:
        return ()

    async def hit(self, **kwargs: Unpack[HitKwargs]) -> RateLimitResult:
        key = f"rl:{self.script_name}:{kwargs["scope"]}:{kwargs["identity"]}"
        window_ms = kwargs["window_seconds"] * 1000
        now_ms = self._get_now_ms()
        extras = self.extra_argv(now_ms=now_ms)

        allowed_flag, retry_after_ms = await redis_client.scripts[self.script_name](
            keys=[key],
            args=[now_ms, window_ms, kwargs["limit"], *extras],
        )

        return RateLimitResult(
            allowed=bool(int(allowed_flag)),
            retry_after_ms=int(retry_after_ms),
        )

    def _get_now_ms(self) -> int:
        return int(utcnow().timestamp() * 1000)


class SlidingWindowLog(RateLimitAlgorithm):
    def __init__(self) -> None:
        super().__init__("sliding_window_log")

    def extra_argv(self, **kwargs: Unpack[ExtraArgvKwargs]) -> tuple[EncodableT, ...]:
        member = f"{kwargs["now_ms"]}:{uuid4()}"
        return (member,)


HITTERS: dict[LuaScriptName, RateLimitAlgorithm] = {
    "fixed_window_counter": RateLimitAlgorithm("fixed_window_counter"),
    "leaky_bucket": RateLimitAlgorithm("leaky_bucket"),
    "sliding_window_counter": RateLimitAlgorithm("sliding_window_counter"),
    "sliding_window_log": SlidingWindowLog(),
    "token_bucket": RateLimitAlgorithm("token_bucket"),
}
