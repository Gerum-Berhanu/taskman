import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.exceptions import AppError
from app.core.request_context import current_user_id_ctx, request_id_ctx


logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        log_fn = logger.warning if exc.status_code < 500 else logger.error
        log_fn(
            "app_error status=%s detail=%s path=%s",
            exc.status_code,
            repr(exc.detail),
            request.url.path,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=exc.headers
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        rid = getattr(request.state, "request_id", "-")
        # put it back so the filter works for this log line
        rid_ctx = request_id_ctx.set(rid)
        try:
            logger.error(
                "unhandled_error path=%s",
                request.url.path,
                exc_info=True,
            )
        finally:
            request_id_ctx.reset(rid_ctx)

        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )
        