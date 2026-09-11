"""Dependency injection wiring for services and auth."""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, Path
from fastapi.security import OAuth2PasswordBearer
from pydantic import UUID4
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.exceptions import WorkspaceForbiddenError
from app.database.session import async_session_factory
from app.database.unit_of_work import UnitOfWork
from app.repositories.user import UserRecord
from app.schemas.workspace import WorkspaceMemberRole
from app.services.auth import AuthService
from app.services.task import TaskService
from app.services.user import UserService
from app.services.workspace import WorkspaceService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def get_uow(session: SessionDep) -> AsyncGenerator[UnitOfWork, None]:
    async with UnitOfWork(session) as uow:
        yield uow


UowDep = Annotated[UnitOfWork, Depends(get_uow)]


def get_task_service(uow: UowDep) -> TaskService:
    return TaskService(uow)


def get_user_service(uow: UowDep) -> UserService:
    return UserService(uow)


def get_auth_service(uow: UowDep) -> AuthService:
    return AuthService(uow)


def get_workspace_service(uow: UowDep) -> WorkspaceService:
    return WorkspaceService(uow)


TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
WorkspaceServiceDep = Annotated[WorkspaceService, Depends(get_workspace_service)]


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    auth_service: AuthServiceDep
) -> UserRecord:
    return await auth_service.get_user_from_token(token)


CurrentUserDep = Annotated[UserRecord, Depends(get_current_user)]


async def require_workspace_owner(
    workspace_id: Annotated[UUID4, Path()],
    current_user: CurrentUserDep,
    workspace_service: WorkspaceServiceDep,
) -> None:
    role = await workspace_service.get_role(workspace_id, current_user.id)
    if role != WorkspaceMemberRole.OWNER.value:
        raise WorkspaceForbiddenError
