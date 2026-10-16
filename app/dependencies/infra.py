"""Dependency injection wiring for DB session and unit of work."""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.infrastructure.database.session import async_session_factory
from app.repositories.unit_of_work import UnitOfWork


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a request-scoped async DB session."""
    async with async_session_factory() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session, scope="function")]


async def get_uow(session: SessionDep) -> AsyncGenerator[UnitOfWork, None]:
    """Yield a UnitOfWork that commits on success and rolls back on error."""
    async with UnitOfWork(session) as uow:
        yield uow


UowDep = Annotated[UnitOfWork, Depends(get_uow, scope="function")]
