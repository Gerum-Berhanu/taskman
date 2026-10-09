"""Structured app log helper: text line + event/fields for JSON."""

import logging

# Field keys that may contain spaces — always repr in the text line.
_REPR_KEYS = frozenset({"detail", "subject"})


def _format_text(event: str, fields: dict[str, object]) -> str:
    if not fields:
        return event
    parts = [event]
    for key, value in fields.items():
        if key in _REPR_KEYS:
            parts.append(f"{key}={value!r}")
        else:
            parts.append(f"{key}={value}")
    return " ".join(parts)


def log_event(
    logger: logging.Logger,
    level: int,
    event: str,
    *,
    exc_info: bool = False,
    **fields: object,
) -> None:
    """Log ``event`` with attrs; JSON gets ``event``/``fields``, text gets one line."""
    payload = dict(fields)
    text = _format_text(event, payload)
    logger.log(
        level,
        text,
        exc_info=exc_info,
        extra={"event": event, "fields": payload},
    )
