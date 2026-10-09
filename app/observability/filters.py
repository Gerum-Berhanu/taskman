"""Logging filters attached to handlers."""

from enum import StrEnum
import logging

from app.core.request_context import request_id_ctx


class LogCategory(StrEnum):
    HTTP = "http"
    DOMAIN = "domain"
    INFRA = "infra"
    OPS = "ops"


# Top-level package under app.* → category (package layout is the taxonomy)
_PACKAGE_CATEGORY: dict[str, LogCategory] = {
    "services": LogCategory.DOMAIN,
    "infrastructure": LogCategory.INFRA,
    "middleware": LogCategory.HTTP,
    "exception_handlers": LogCategory.HTTP,
    "repositories": LogCategory.OPS,
    "main": LogCategory.OPS,
}


class CategoryFilter(logging.Filter):
    """Attach envelope category from the logger name onto each log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        parts = record.name.split(".")
        if len(parts) >= 2 and parts[0] == "app":
            record.category = _PACKAGE_CATEGORY.get(parts[1], LogCategory.OPS)
        else:
            record.category = LogCategory.OPS
        return True


class RequestIdFilter(logging.Filter):
    """Attach the current request id onto each log record."""

    # filters run before formatters
    def filter(self, record: logging.LogRecord) -> bool:
        # get request_id associated with the current async task (coroutine)
        record.request_id = request_id_ctx.get()
        return True
