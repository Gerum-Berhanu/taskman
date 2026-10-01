"""Load Redis Lua scripts packaged under ``scripts/``."""

from importlib.resources import files


def load_lua(name: str) -> str:
    """Return the source text of a packaged ``.lua`` script by filename."""
    return files("app.infrastructure.redis.scripts").joinpath(name).read_text(encoding="utf-8")


SLIDING_WINDOW_LOG = load_lua("sliding_window_log.lua")
