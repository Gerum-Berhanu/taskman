"""Application-level exceptions (mapped to HTTP in the API layer)."""

from starlette.status import HTTP_400_BAD_REQUEST, HTTP_401_UNAUTHORIZED, HTTP_404_NOT_FOUND


class AppError(Exception):
    status_code: int = 500
    detail: str = "Internal server error"
    headers: dict[str, str] | None = None


class EmailAlreadyRegisteredError(AppError):
    status_code = HTTP_400_BAD_REQUEST
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


class MembershipTargetNotFound(AppError):
    status_code = HTTP_404_NOT_FOUND
    detail = "Workspace or user not found"
