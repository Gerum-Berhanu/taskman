"""Log record formatters for text and JSON envelopes."""

import json
import logging


_DATEFMT = "%Y-%m-%d %H:%M:%SZ"
_TEXT_FMT = (
    "%(asctime)s | %(levelname)s | %(category)s | %(name)s | %(request_id)s | %(message)s"
)


class DefaultFormatter(logging.Formatter):
    """Human-readable text envelope."""

    def __init__(self) -> None:
        super().__init__(fmt=_TEXT_FMT, datefmt=_DATEFMT)


class JsonFormatter(logging.Formatter):
    """Format log records as single-line JSON objects."""

    def __init__(self) -> None:
        super().__init__(datefmt=_DATEFMT)

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "category": getattr(record, "category", "ops"),
            "logger": record.name,
            "request_id": getattr(record, "request_id", "-"),
        }
        event = getattr(record, "event", None)
        if event is not None:
            payload["event"] = event
            payload["fields"] = getattr(record, "fields", {})
        else:
            payload["message"] = record.getMessage()
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)
