from fastapi import FastAPI

from app.core.middlewares import (
    LogMiddleware, 
    RateLimitMiddleware,
    RequestIdMiddleware,
)


def register_middlewares(app: FastAPI) -> None:
    app.add_middleware(LogMiddleware)
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(RateLimitMiddleware)
