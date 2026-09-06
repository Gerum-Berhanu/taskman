"""Unit of Work: one transaction boundary for all repositories."""

from sqlmodel.ext.asyncio.session import AsyncSession

from app.repositories.task import SqlTaskRepository
from app.repositories.user import SqlUserRepository


class UnitOfWork:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = SqlUserRepository(session)
        self.tasks = SqlTaskRepository(session)

    async def __aenter__(self) -> "UnitOfWork":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if exc_type is None:
            await self.session.commit()
        else:
            await self.session.rollback()