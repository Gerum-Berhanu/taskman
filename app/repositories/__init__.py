"""Persistence repositories - one SQL implementation per domain."""

from app.dto.repository import (
    ClientSessionCreateData,
    ClientSessionRecord,
    RefreshTokenCreateData,
    RefreshTokenRecord,
    TaskCreateData,
    TaskRecord,
    TaskUpdateData,
    UserCreateData,
    UserRecord,
    WorkspaceCreateData,
    WorkspaceMemberCreateData,
    WorkspaceMemberRecord,
    WorkspaceRecord,
)
from app.repositories.client_session import ClientSessionRepository
from app.repositories.refresh_token import RefreshTokenRepository
from app.repositories.task import TaskRepository
from app.repositories.unit_of_work import UnitOfWork
from app.repositories.user import UserRepository
from app.repositories.workspace import WorkspaceRepository
from app.repositories.workspace_member import WorkspaceMemberRepository

__all__ = [
    "ClientSessionCreateData",
    "ClientSessionRecord",
    "ClientSessionRepository",
    "RefreshTokenCreateData",
    "RefreshTokenRecord",
    "RefreshTokenRepository",
    "TaskCreateData",
    "TaskRecord",
    "TaskRepository",
    "TaskUpdateData",
    "UnitOfWork",
    "UserCreateData",
    "UserRecord",
    "UserRepository",
    "WorkspaceCreateData",
    "WorkspaceMemberCreateData",
    "WorkspaceMemberRecord",
    "WorkspaceMemberRepository",
    "WorkspaceRecord",
    "WorkspaceRepository",
]
