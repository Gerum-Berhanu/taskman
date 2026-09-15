from pydantic import BaseModel
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession


async def add_flush_refresh[T](session: AsyncSession, entity: T) -> T:
    """Add entity, flush, and refresh so DB-generated fields are loaded."""
    session.add(entity)
    await session.flush()
    await session.refresh(entity)
    return entity


def to_record[T: BaseModel](record_class: type[T], orm_object: SQLModel) -> T:
    return record_class.model_validate(orm_object)
    