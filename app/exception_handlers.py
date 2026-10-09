"""Map application and unexpected errors to JSON HTTP responses."""

import logging
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.exceptions import AppError
from app.core.request_context import request_id_ctx
from app.observability.events import HttpLogEvent


logger = logging.getLogger(__name__)

_HTTP_ERROR_FMT = "%s method=%s path=%s status=%s detail=%s actor_id=%s"


def register_exception_handlers(app: FastAPI) -> None:
    """Register handlers for AppError, RequestValidationError, and bare Exception."""

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        actor_id = getattr(request.state, "actor_id", "-")

        log_fn = logger.warning if exc.status_code < 500 else logger.error
        log_fn(
            _HTTP_ERROR_FMT,
            HttpLogEvent.APP_ERROR,
            request.method,
            request.url.path,
            exc.status_code,
            repr(exc.detail),
            actor_id,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=exc.headers
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        rid = getattr(request.state, "request_id", "-")
        actor_id = getattr(request.state, "actor_id", "-")

        # put it back so the filter, enabling %(request_id)s, works for this log line
        rid_ctx = request_id_ctx.set(rid)

        try:
            logger.exception(
                _HTTP_ERROR_FMT,
                HttpLogEvent.UNHANDLED_ERROR,
                request.method,
                request.url.path,
                500,
                "Something went wrong",
                actor_id,
            )
        finally:
            request_id_ctx.reset(rid_ctx)

        return JSONResponse(
            status_code=500,
            content={"detail": "Something went wrong"},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        actor_id = getattr(request.state, "actor_id", "-")

        errors = exc.errors()
        if errors:
            err = errors[0]
            loc = err["loc"][-1]
            msg = err["msg"]
            detail = f"{msg} at {loc}"
        else:
            detail = "Invalid request"

        logger.warning(
            _HTTP_ERROR_FMT,
            HttpLogEvent.VALIDATION_ERROR,
            request.method,
            request.url.path,
            422,
            repr(detail),
            actor_id,
        )

        return JSONResponse(
            status_code=422,
            content={"detail": detail},
        )
        
