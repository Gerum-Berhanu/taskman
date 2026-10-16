"""Application exceptions and FastAPI error handlers."""

from app.exceptions.handlers import register_exception_handlers
from app.exceptions.types import (
    AppError,
    AssigneeNotInWorkspaceError,
    EmailAlreadyRegisteredError,
    FailedDatabaseConnection,
    InvalidCredentialsError,
    InvalidTokenError,
    MembershipAlreadyExistsError,
    RateLimitExceededError,
    TaskNotFoundError,
    UnknownClientError,
    UserNotFoundError,
    WorkspaceForbiddenError,
)

__all__ = [
    "AppError",
    "AssigneeNotInWorkspaceError",
    "EmailAlreadyRegisteredError",
    "FailedDatabaseConnection",
    "InvalidCredentialsError",
    "InvalidTokenError",
    "MembershipAlreadyExistsError",
    "RateLimitExceededError",
    "TaskNotFoundError",
    "UnknownClientError",
    "UserNotFoundError",
    "WorkspaceForbiddenError",
    "register_exception_handlers",
]
