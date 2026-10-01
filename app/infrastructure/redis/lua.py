"""Load Redis Lua scripts packaged under scripts/."""

from importlib.resources import files
from typing import Literal, get_args


LuaScriptName = Literal["sliding_window_counter", "sliding_window_log"]


def load_all_lua() -> dict[LuaScriptName, str]:
    """Load each declared script by name; raise if a file is missing."""
    scripts_dir = files("app.infrastructure.redis.scripts")
    loaded: dict[LuaScriptName, str] = {}
    for name in get_args(LuaScriptName):
        path = scripts_dir.joinpath(f"{name}.lua")
        try:
            loaded[name] = path.read_text(encoding="utf-8")
        except (FileNotFoundError, OSError) as exc:
            raise FileNotFoundError(f"Missing Lua script: {name}.lua") from exc
    return loaded


LUA_SCRIPTS: dict[LuaScriptName, str] = load_all_lua()
