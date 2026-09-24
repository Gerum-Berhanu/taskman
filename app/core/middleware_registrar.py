from fastapi import FastAPI

from app.core.middlewares import LogMiddleware, RequestIdMiddleware


def register_middlewares(app: FastAPI) -> None:
    app.add_middleware(LogMiddleware)
    app.add_middleware(RequestIdMiddleware)
