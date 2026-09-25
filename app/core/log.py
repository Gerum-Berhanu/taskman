"""Centralized logging setup."""

import json
import logging
from pathlib import Path
import sys

from app.core.config import settings
from app.core.request_context import request_id_ctx


_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_LOG_DIR = _PROJECT_ROOT / "logs"
_DATEFMT = "%Y-%m-%d %H:%M:%S"


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
        return JsonFormatter(datefmt=_DATEFMT)
    return logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(request_id)s | %(message)s",
        datefmt=_DATEFMT,
    )


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
        file_handler = logging.FileHandler(_LOG_DIR / "app.log", mode="a")
        file_handler.setFormatter(formatter)
        file_handler.addFilter(rid_filter)
        root.addHandler(file_handler)

    # logger.debug() don't spam wheen root is at DEBUG level
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
