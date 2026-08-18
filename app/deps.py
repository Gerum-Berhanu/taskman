"""Dependency injection wiring for services and auth."""

from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from pydantic import UUID4
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_404_NOT_FOUND

from app.database.records import TaskRecord, UserRecord
from app.database.repositories import (
    TaskRepository,
    UserRepository,
    task_repository,
    user_repository,
)
from app.services.auth_service import AuthService
from app.services.task_service import TaskService
from app.services.user_service import UserService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def get_task_repository() -> TaskRepository:
    return task_repository


def get_user_repository() -> UserRepository:
    return user_repository


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
    credentials_exception = HTTPException(
        status_code=HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    user = auth_service.get_user_from_token(token)
    if user is None:
        raise credentials_exception
    return user


CurrentUserDep = Annotated[UserRecord, Depends(get_current_user)]


def get_task_or_404(
    task_id: UUID4,
    service: TaskServiceDep,
) -> TaskRecord:
    task = service.get(task_id)
    if task is None:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    return task


TaskDep = Annotated[TaskRecord, Depends(get_task_or_404)]
