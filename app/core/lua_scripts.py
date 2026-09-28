from importlib.resources import files


def load_lua(name: str) -> str:
    return files("app.core.lua").joinpath(name).read_text(encoding="utf-8")


SLIDING_WINDOW = load_lua("sliding_window_rate_limit.lua")
