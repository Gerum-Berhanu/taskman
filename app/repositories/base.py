from pydantic import BaseModel
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession


class BaseRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_flush_refresh[T](self, entity: T) -> T:
        """Add entity, flush, and refresh so DB-generated fields are loaded."""
        self._session.add(entity)
        await self._session.flush()
        await self._session.refresh(entity)
        return entity

    async def flush_refresh[T](self, entity: T) -> T:
        """Flush and refresh a tracked entity (updates; no add)."""
        await self._session.flush()
        await self._session.refresh(entity)
        return entity

    def to_record[T: BaseModel](
        self, record_class: type[T], orm_object: SQLModel
    ) -> T:
        """Map an ORM instance to a repository record model."""
        return record_class.model_validate(orm_object)
