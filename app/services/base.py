"""Shared application service helpers."""

import logging

from app.observability.events import LogEvent
from app.observability.log_event import log_event
from app.repositories.unit_of_work import UnitOfWork


class BaseService:
    """Thin base holding the UoW and after-commit domain log helper."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def log_after_commit(
        self,
        event: LogEvent,
        /,
        *,
        level: int = logging.INFO,
        exc_info: bool = False,
        **fields: object,
    ) -> None:
        """Queue a domain ``log_event`` to run after a successful commit."""
        logger = logging.getLogger(type(self).__module__)
        self._uow.after_commit(
            lambda: log_event(logger, level, event, exc_info=exc_info, **fields)
        )
