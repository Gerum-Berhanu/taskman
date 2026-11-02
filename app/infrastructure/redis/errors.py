"""Shared Redis data-path exception groups."""

import json

from redis.exceptions import RedisError

# get/set/delete of JSON values (not connect/init).
REDIS_DATA_ERRORS = (RedisError, TimeoutError, json.JSONDecodeError)
