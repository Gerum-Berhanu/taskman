"""Register ASGI middleware on the FastAPI application."""

from fastapi import FastAPI

from app.middleware import (
    AccessLogMiddleware,
    RequestIdMiddleware,
)


def register_middlewares(app: FastAPI) -> None:
    """Add middlewares in Starlette LIFO order: last added runs first on the request."""
    app.add_middleware(AccessLogMiddleware)
    app.add_middleware(RequestIdMiddleware)
