"""Shared repository helpers for flush/refresh and ORM-to-record mapping."""

from pydantic import BaseModel
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession


class BaseRepository[
    ModelT: SQLModel, 
    RecordT: BaseModel, 
    CreateT: BaseModel, 
]:
    """Thin base holding the session and common persistence helpers."""

    model: type[ModelT]
    record: type[RecordT]

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, fields: CreateT) -> RecordT:
        instance = self.model(**fields.model_dump())
        await self._add_flush_refresh(instance)
        return self._to_record(instance)

    async def get(self, *identity: object) -> RecordT | None:
        pk = identity[0] if len(identity) == 1 else identity
        result = await self._session.get(self.model, pk)
        if result is None:
            return None
        return self._to_record(result)

    async def _add_flush_refresh(self, entity: ModelT) -> ModelT:
        """Add entity, flush, and refresh so DB-generated fields are loaded."""
        self._session.add(entity)
        await self._session.flush()
        await self._session.refresh(entity)
        return entity

    async def _flush_refresh(self, entity: ModelT) -> ModelT:
        """Flush and refresh a tracked entity (updates; no add)."""
        await self._session.flush()
        await self._session.refresh(entity)
        return entity

    def _to_record(self, entity: ModelT) -> RecordT:
        """Map an ORM instance to a repository record model."""
        return self.record.model_validate(entity)
