"""Unit of Work: one transaction boundary for all repositories."""

from collections.abc import Callable

from sqlmodel.ext.asyncio.session import AsyncSession

from app.repositories import (
    ClientSessionRepository,
    RefreshTokenRepository,
    TaskRepository,
    UserRepository,
    WorkspaceMemberRepository,
    WorkspaceRepository,
)


class UnitOfWork:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.tasks = TaskRepository(session)
        self.refresh_tokens = RefreshTokenRepository(session)
        self.client_sessions = ClientSessionRepository(session)
        self.workspaces = WorkspaceRepository(session)
        self.workspace_members = WorkspaceMemberRepository(session)
        self._after_commit: list[Callable[[], None]] = []

    def after_commit(self, callback: Callable[[], None]) -> None:
        """Run callback after a successful commit (skipped on rollback)."""
        self._after_commit.append(callback)

    async def __aenter__(self) -> "UnitOfWork":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if exc_type is None:
            await self.session.commit()
            for callback in self._after_commit:
                callback()
        else:
            await self.session.rollback()
        self._after_commit.clear()
