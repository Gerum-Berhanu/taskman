"""Register ASGI middleware on the FastAPI application."""

from fastapi import FastAPI

from app.middleware import (
    AccessLogMiddleware,
    RateLimitMiddleware,
    RequestIdMiddleware,
)


def register_middlewares(app: FastAPI) -> None:
    """Add rate-limit, request-id, and access-log middleware (Starlette LIFO order)."""
    # Starlette stacks middleware LIFO: last added runs first on the request.
    app.add_middleware(AccessLogMiddleware)
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(RateLimitMiddleware)
