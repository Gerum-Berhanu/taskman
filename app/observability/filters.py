"""Logging filters attached to handlers."""

import logging

from app.core.request_context import request_id_ctx


class RequestIdFilter(logging.Filter):
    """Attach the current request id onto each log record."""

    # filters run before formatters
    def filter(self, record: logging.LogRecord) -> bool:
        # get request_id associated with the current async task (coroutine)
        record.request_id = request_id_ctx.get() 
        return True
