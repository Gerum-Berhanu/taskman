"""Application-level exceptions (mapped to HTTP in the API layer)."""

from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
    HTTP_503_SERVICE_UNAVAILABLE,
)


class AppError(Exception):
    status_code: int = 500
    detail: str = "Internal server error"
    headers: dict[str, str] | None = None


class EmailAlreadyRegisteredError(AppError):
    status_code = HTTP_409_CONFLICT
    detail = "Account with this email already exists"


class TaskNotFoundError(AppError):
    status_code = HTTP_404_NOT_FOUND
    detail = "Task not found"


class InvalidCredentialsError(AppError):
    status_code = HTTP_401_UNAUTHORIZED
    detail = "Incorrect email or password"
    headers = {"WWW-Authenticate": "Bearer"}


class InvalidTokenError(AppError):
    status_code = HTTP_401_UNAUTHORIZED
    detail = "Could not validate credentials"
    headers = {"WWW-Authenticate": "Bearer"}


class UserNotFoundError(AppError):
    status_code = HTTP_404_NOT_FOUND
    detail = "User not found"


class WorkspaceForbiddenError(AppError):
    status_code = HTTP_403_FORBIDDEN
    detail = "Insufficient workspace permissions"


class MembershipAlreadyExistsError(AppError):
    status_code = HTTP_409_CONFLICT
    detail = "Member is already in the workspace"


class AssigneeNotInWorkspaceError(AppError):
    status_code = HTTP_400_BAD_REQUEST
    detail = "Assignee is not a member of the workspace"


class FailedDatabaseConnection(AppError):
    status_code = HTTP_503_SERVICE_UNAVAILABLE
    detail = "Database connection failed"
