"""Unit of Work: one transaction boundary for all repositories."""

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

    async def __aenter__(self) -> "UnitOfWork":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if exc_type is None:
            await self.session.commit()
        else:
            await self.session.rollback()
