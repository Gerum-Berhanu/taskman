"""Combined Redis ops surface for RedisClient."""

from app.infrastructure.redis.ops.hash import HashOpsMixin
from app.infrastructure.redis.ops.json import JsonOpsMixin
from app.infrastructure.redis.ops.keys import KeysOpsMixin


class RedisOps(JsonOpsMixin, HashOpsMixin, KeysOpsMixin):
    """All Redis helper methods; connection lifecycle lives on RedisClient."""
