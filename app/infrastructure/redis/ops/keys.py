"""Key-level helpers on the shared async Redis client."""

from app.infrastructure.redis.client import redis_client


async def key_exists(key: str) -> bool:
    """Return True when the key exists."""
    client = redis_client.get_redis_client
    return bool(await client.exists(key))


async def delete_keys(*keys: str) -> None:
    """Delete one or more keys (no-op if empty)."""
    if not keys:
        return
    client = redis_client.get_redis_client
    await client.delete(*keys)
