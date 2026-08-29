"""Dependency injection wiring for services and auth."""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database.session import async_session_factory
from app.repositories.records import UserRecord
from app.repositories.task_repo import SqlTaskRepository, TaskRepository
from app.repositories.user_repo import SqlUserRepository, UserRepository
from app.services.auth_service import AuthService
from app.services.task_service import TaskService
from app.services.user_service import UserService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]


def get_task_repository(session: SessionDep) -> TaskRepository:
    return SqlTaskRepository(session)


def get_user_repository(session: SessionDep) -> UserRepository:
    return SqlUserRepository(session)


def get_task_service(
    repository: Annotated[TaskRepository, Depends(get_task_repository)],
) -> TaskService:
    return TaskService(repository)


def get_user_service(
    repository: Annotated[UserRepository, Depends(get_user_repository)],
) -> UserService:
    return UserService(repository)


def get_auth_service(
    repository: Annotated[UserRepository, Depends(get_user_repository)],
) -> AuthService:
    return AuthService(repository)


TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    auth_service: AuthServiceDep
) -> UserRecord:
    return await auth_service.get_user_from_token(token)


CurrentUserDep = Annotated[UserRecord, Depends(get_current_user)]
