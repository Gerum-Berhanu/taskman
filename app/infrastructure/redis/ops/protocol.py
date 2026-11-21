"""Structural typing for Redis ops mixins."""

from typing import Protocol

from redis.asyncio import Redis


class RedisConn(Protocol):
    """Anything that exposes a live redis-py client (e.g. RedisClient)."""

    @property
    def get_client(self) -> Redis: ...
