"""Map application and unexpected errors to JSON HTTP responses."""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.exceptions import AppError
from app.core.request_context import request_id_ctx
from app.observability.events import HttpLogEvent
from app.observability.log_event import log_event


logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """Register AppError, RequestValidationError, and bare Exception handlers."""

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        level = logging.WARNING if exc.status_code < 500 else logging.ERROR
        log_event(
            logger,
            level,
            HttpLogEvent.APP_ERROR,
            actor_id=getattr(request.state, "actor_id", "-"),
            detail=exc.detail,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=exc.headers,
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        rid = getattr(request.state, "request_id", "-")
        # put it back so the filter, enabling %(request_id)s, works for this log line
        rid_ctx = request_id_ctx.set(rid)
        detail = "Something went wrong"
        try:
            log_event(
                logger,
                logging.ERROR,
                HttpLogEvent.UNHANDLED_ERROR,
                exc_info=True,
                actor_id=getattr(request.state, "actor_id", "-"),
                detail=detail,
            )
        finally:
            request_id_ctx.reset(rid_ctx)

        return JSONResponse(status_code=500, content={"detail": detail})

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errors = exc.errors()
        if errors:
            err = errors[0]
            msg = err.get("msg", "Invalid request")
            loc = err.get("loc") or ()
            detail = f"{msg} at {loc[-1]}" if loc else msg
        else:
            detail = "Invalid request"

        log_event(
            logger,
            logging.WARNING,
            HttpLogEvent.VALIDATION_ERROR,
            actor_id=getattr(request.state, "actor_id", "-"),
            detail=detail,
        )

        return JSONResponse(status_code=422, content={"detail": detail})
