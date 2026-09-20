import logging
import time
from typing import Any
from uuid import UUID, uuid4
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


logger = logging.getLogger(__name__)


class AppMiddleware(BaseHTTPMiddleware):
    """Place for shared helpers"""
    pass


class RequestIDMiddleware(AppMiddleware):
    async def dispatch(self, request: Request, call_next):
        """Save a request id either from X-Request-ID header or newly generated"""
        presented_id = request.headers.get("X-Request-ID")
        if not presented_id:
            request_id = uuid4()
        else:
            try:
                request_id = UUID(presented_id, version=4)
            except ValueError:
                request_id = uuid4()

        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = str(request_id)
        return response


class LogMiddleware(AppMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.perf_counter()

        response = await call_next(request)
        process_time = time.perf_counter() - start_time

        log_dict = {
            "request_id": request.state.request_id,
            "url": request.url.path,
            "method": request.method,
            "status_code": response.status_code,
            "process_time": round(process_time, 5),
        }
        logger.info(log_dict)
        return response
        