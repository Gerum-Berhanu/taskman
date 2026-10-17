"""Logging filters attached to handlers."""

from enum import StrEnum
import logging

from app.core.request_context import request_id_ctx


class LogCategory(StrEnum):
    HTTP = "http"
    DOMAIN = "domain"
    INFRA = "infra"
    OPS = "ops"


# Logger-name prefixes → envelope category. Longest match wins via walk-up.
_PACKAGE_CATEGORY: dict[str, LogCategory] = {
    "app.services": LogCategory.DOMAIN,
    "app.infrastructure": LogCategory.INFRA,
    "app.dependencies.rate_limit": LogCategory.HTTP,
    "app.middleware": LogCategory.HTTP,
    "app.exceptions": LogCategory.HTTP,
    "app.repositories": LogCategory.OPS,
    "app.jobs": LogCategory.OPS,
    "app.main": LogCategory.OPS,
}


def _category(name: str) -> LogCategory:
    while name:
        if name in _PACKAGE_CATEGORY:
            return _PACKAGE_CATEGORY[name]
        name = name.rpartition(".")[0]
    return LogCategory.OPS


class CategoryFilter(logging.Filter):
    """Attach envelope category from the logger name onto each log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.category = _category(record.name)
        return True


class RequestIdFilter(logging.Filter):
    """Attach the current request id onto each log record."""

    # filters run before formatters
    def filter(self, record: logging.LogRecord) -> bool:
        # get request_id associated with the current async task (coroutine)
        record.request_id = request_id_ctx.get()
        return True
