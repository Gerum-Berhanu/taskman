"""Dependency injection wiring for services and auth."""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database.session import async_session_factory
from app.database.unit_of_work import UnitOfWork
from app.schemas.user import UserRead
from app.services.auth import AuthService
from app.services.task import TaskService
from app.services.user import UserService
from app.services.workspace import WorkspaceService
from app.services.workspace_member import WorkspaceMemberService

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


def get_workspace_member_service(uow: UowDep) -> WorkspaceMemberService:
    return WorkspaceMemberService(uow)


TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
WorkspaceServiceDep = Annotated[WorkspaceService, Depends(get_workspace_service)]
WorkspaceMemberServiceDep = Annotated[
    WorkspaceMemberService, Depends(get_workspace_member_service)
]


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    auth_service: AuthServiceDep
) -> UserRead:
    return await auth_service.get_user_from_token(token)


CurrentUserDep = Annotated[UserRead, Depends(get_current_user)]
