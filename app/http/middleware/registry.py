from fastapi import FastAPI

from app.http.middleware.rate_limit import RateLimitMiddleware
from app.http.middleware.request_id import RequestIdMiddleware
from app.http.middleware.request_logging import LogMiddleware


def register_middlewares(app: FastAPI) -> None:
    # Starlette stacks middleware LIFO: last added runs first on the request.
    app.add_middleware(LogMiddleware)
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(RateLimitMiddleware)
