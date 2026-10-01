from dataclasses import dataclass
from uuid import uuid4

from app.core.timeutils import utcnow
from app.infrastructure.redis.client import redis_client


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    count: int
    limit: int


async def hit_sliding_window(
    policy: str, identity: str, limit: int, window_seconds: int
) -> RateLimitResult:
    """
    policy: Rule set to apply ("default" vs "auth")
    identity: Client IP
    limit: Allowed number of requests
    window_seconds: Limit period/interval

    key: Custom construct to uniquely identify a client's rate status
    """
    key = f"rl:{policy}:{identity}"
    now_ms = int(utcnow().timestamp() * 1000)
    window_ms = window_seconds * 1000
    member = f"{now_ms}:{uuid4()}"

    script = redis_client.sliding_window_script
    allowed_flag, count = await script(
        keys=[key],
        args=[now_ms, window_ms, limit, member],
    )

    return RateLimitResult(
        allowed=bool(int(allowed_flag)),
        count=int(count),
        limit=limit,
    )
