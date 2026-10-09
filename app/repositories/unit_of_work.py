"""Unit of Work: one transaction boundary for all repositories."""

import logging
from collections.abc import Callable

from sqlmodel.ext.asyncio.session import AsyncSession

from app.observability.events import OpsLogEvent
from app.repositories.client_session import ClientSessionRepository
from app.repositories.refresh_token import RefreshTokenRepository
from app.repositories.task import TaskRepository
from app.repositories.user import UserRepository
from app.repositories.workspace import WorkspaceRepository
from app.repositories.workspace_member import WorkspaceMemberRepository


logger = logging.getLogger(__name__)


class UnitOfWork:
    """One DB transaction with repository accessors and after-commit hooks."""

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
        """Commit the session, then run queued after-commit callbacks."""
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
                logger.exception(OpsLogEvent.AFTER_COMMIT_FAILED)

    async def rollback(self) -> None:
        """Roll back the session and discard pending after-commit callbacks."""
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
