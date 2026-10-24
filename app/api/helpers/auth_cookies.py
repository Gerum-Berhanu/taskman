"""HttpOnly auth cookie helpers for routes (services stay cookie-agnostic)."""

from typing import Annotated

from fastapi import Cookie, Response

from app.core.config import AppEnv, settings

RefreshTokenCookie = Annotated[
    str | None, Cookie(alias=settings.refresh_token_cookie_name)
]


def _cookie_common() -> dict:
    return {
        "httponly": True,
        "samesite": "lax",
        "secure": settings.app_env != AppEnv.DEVELOPMENT,
        "path": "/",
    }


def set_refresh_cookie(response: Response, raw_token: str) -> None:
    response.set_cookie(
        key=settings.refresh_token_cookie_name,
        value=raw_token,
        max_age=settings.refresh_token_expire_minutes * 60,
        **_cookie_common(),
    )


def clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.refresh_token_cookie_name,
        **_cookie_common(),
    )
