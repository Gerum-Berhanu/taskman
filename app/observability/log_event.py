"""Structured app log helper: text line + event/fields for JSON."""

from collections.abc import Callable
from functools import partial
import logging
from typing import Protocol


# Field keys that may contain spaces - always repr in the text line.
_REPR_KEYS = frozenset({"detail", "subject"})


class SupportsAfterCommit(Protocol):
    """Anything that can queue a zero-arg callback until after a successful commit."""

    def after_commit(self, callback: Callable[[], None]) -> None: ...


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


def _emit_event(
    logger: logging.Logger,
    level: int,
    event: str,
    fields: dict[str, object],
    *,
    exc_info: bool = False,
) -> None:
    logger.log(
        level,
        _format_text(event, fields),
        exc_info=exc_info,
        extra={"event": event, "fields": fields},
    )


def log_event(
    logger: logging.Logger,
    level: int,
    event: str,
    *,
    after_commit: SupportsAfterCommit | None = None,
    exc_info: bool = False,
    **fields: object,
) -> None:
    """Log event now, or queue on after_commit until a successful UoW commit."""
    if after_commit is not None:
        after_commit.after_commit(
            partial(_emit_event, logger, level, event, fields, exc_info=exc_info)
        )
        return
    _emit_event(logger, level, event, fields, exc_info=exc_info)
