"""Unit of Work: one transaction boundary for all repositories."""

import logging
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


logger = logging.getLogger(__name__)


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
        """Queue a callback to run after a successful commit."""
        self._after_commit.append(callback)

    async def commit(self) -> None:
        try:
            await self.session.commit()
        except Exception:
            # No callback should run when the database commit fails.
            self._after_commit.clear()
            raise

        # Detach the callbacks before executing them.
        # This prevents a failed callback from leaving them queued.
        callbacks = self._after_commit
        self._after_commit = []

        for callback in callbacks:
            try:
                callback()
            except Exception:
                # Logging must never turn a successful database operation
                # into a failed API request.
                logger.exception("after_commit_failed")

    async def rollback(self) -> None:
        try:
            await self.session.rollback()
        finally:
            # Rollback means the related domain events must not run.
            self._after_commit.clear()

    async def __aenter__(self) -> "UnitOfWork":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if exc_type is None:
            await self.commit()
        else:
            await self.rollback()