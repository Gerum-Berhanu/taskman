"""Shared repository helpers for flush/refresh and ORM-to-record mapping."""

from pydantic import BaseModel
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession


class BaseRepository[ModelT: SQLModel, RecordT: BaseModel]:
    """Thin base holding the session and common persistence helpers."""

    record: type[RecordT]

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_flush_refresh(self, entity: ModelT) -> ModelT:
        """Add entity, flush, and refresh so DB-generated fields are loaded."""
        self._session.add(entity)
        await self._session.flush()
        await self._session.refresh(entity)
        return entity

    async def flush_refresh(self, entity: ModelT) -> ModelT:
        """Flush and refresh a tracked entity (updates; no add)."""
        await self._session.flush()
        await self._session.refresh(entity)
        return entity

    def to_record(self, entity: ModelT) -> RecordT:
        """Map an ORM instance to a repository record model."""
        return self.record.model_validate(entity)
