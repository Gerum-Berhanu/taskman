"""Shared application service helpers."""

from app.repositories.unit_of_work import UnitOfWork


class BaseService:
    """Thin base holding the request-scoped UnitOfWork."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow
