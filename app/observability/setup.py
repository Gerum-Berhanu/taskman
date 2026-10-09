"""Centralized logging setup."""

import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
import sys
import time

from app.core.config import settings
from app.observability.filters import CategoryFilter, RequestIdFilter
from app.observability.formatters import DefaultFormatter, JsonFormatter


_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_LOG_DIR = _PROJECT_ROOT / "logs"

_NOISY_LOGGERS = (
    "aiosqlite",
    "asyncio",
    "redis.asyncio.connection",
    "sqlalchemy.engine",
    "uvicorn.access",
)


def _build_formatter() -> logging.Formatter:
    """Build the text or JSON formatter based on settings."""
    formatter: logging.Formatter = (
        JsonFormatter() if settings.log_json else DefaultFormatter()
    )
    formatter.converter = time.gmtime
    return formatter


def _attach_to_root(
    handler: logging.Handler,
    formatter: logging.Formatter,
    filters: tuple[logging.Filter, ...],
) -> None:
    """Attach handler, formatter, and filters to the root logger."""
    root = logging.getLogger()
    handler.setFormatter(formatter)
    for f in filters:
        handler.addFilter(f)
    root.addHandler(handler)


def setup_logging() -> None:
    """Configure root handlers, formatters, and noisy third-party log levels."""
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(settings.log_level)

    formatter = _build_formatter()
    filters = (RequestIdFilter(), CategoryFilter())

    _attach_to_root(logging.StreamHandler(sys.stdout), formatter, filters)

    if settings.log_file:
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        file_handler = TimedRotatingFileHandler(
            _LOG_DIR / "app.log",
            when="midnight",
            backupCount=7,
            encoding="utf-8",
            utc=True,
        )
        _attach_to_root(file_handler, formatter, filters)

    # logger.debug() external packages won't spam when root is at DEBUG level
    # because they do logger.debug() but their logger's level only logs out above WARNING
    for name in _NOISY_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)
