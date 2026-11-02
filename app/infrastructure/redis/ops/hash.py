"""Hash get/set/incr helpers on the shared async Redis client."""

from collections.abc import Mapping

from app.infrastructure.redis.client import redis_client


async def set_hash(
    key: str,
    mapping: Mapping[str, str],
    *,
    ttl_seconds: int,
) -> None:
    """Store a hash and set TTL (seconds). Field values must already be strings."""
    client = redis_client.get_redis_client
    await client.hset(key, mapping=dict(mapping))
    await client.expire(key, ttl_seconds)


async def get_hash(key: str) -> dict[str, str] | None:
    """Return all hash fields, or None when the key is missing/empty."""
    client = redis_client.get_redis_client
    data = await client.hgetall(key)
    if not data:
        return None
    return data


async def hincrby(key: str, field: str, amount: int = 1) -> int:
    """Atomically increment a hash integer field; returns the new value."""
    client = redis_client.get_redis_client
    return int(await client.hincrby(key, field, amount))
