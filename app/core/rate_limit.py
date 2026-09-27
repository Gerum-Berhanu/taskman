from dataclasses import dataclass

from redis.asyncio import Redis


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    count: int
    limit: int


async def hit_fixed_window(
    redis: Redis, *, policy: str, identity: str, limit: int, window_seconds: int
) -> RateLimitResult:
    """
    redis: Redis client
    policy: Rule set to apply ("default" vs "auth")
    identity: Client IP
    limit: Allowed number of requests
    window_seconds: Limit period/interval

    key: Custom construct to uniquely identify a client's rate status
    """
    key = f"rl:{policy}:{identity}"
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, window_seconds)
    return RateLimitResult(allowed=count <= limit, count=count, limit=limit)
    