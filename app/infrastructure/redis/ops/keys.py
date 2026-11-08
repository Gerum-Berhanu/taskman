"""Key-level helpers on the shared async Redis client."""

from app.infrastructure.redis.client import redis_client


async def delete_keys(*keys: str) -> None:
    """Delete one or more keys (no-op if empty)."""
    if not keys:
        return
    client = redis_client.get_redis_client
    await client.delete(*keys)
