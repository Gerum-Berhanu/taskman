"""Centralized logging setup."""

import json
import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
import sys
import time

from app.core.config import settings
from app.core.request_context import request_id_ctx


_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_LOG_DIR = _PROJECT_ROOT / "logs"
_DATEFMT = "%Y-%m-%d %H:%M:%SZ"


class RequestIdFilter(logging.Filter):
    # filters run before formatters
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get() # get request_id associated with the current task
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "request_id": getattr(record, "request_id", "-"),
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def _build_formatter() -> logging.Formatter:
    if settings.log_json:
        formatter: logging.Formatter = JsonFormatter(datefmt=_DATEFMT)
    else:
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(request_id)s | %(message)s",
            datefmt=_DATEFMT,
        )
    formatter.converter = time.gmtime
    return formatter


def setup_logging() -> None:
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(settings.log_level)

    formatter = _build_formatter()
    rid_filter = RequestIdFilter()

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    console.addFilter(rid_filter)
    root.addHandler(console)

    if settings.log_file:
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        file_handler = TimedRotatingFileHandler(
            _LOG_DIR / "app.log",
            when="midnight",
            backupCount=7,
            encoding="utf-8",
            utc=True,
        )
        file_handler.setFormatter(formatter)
        file_handler.addFilter(rid_filter)
        root.addHandler(file_handler)

    # logger.debug() don't spam when root is at DEBUG level
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
