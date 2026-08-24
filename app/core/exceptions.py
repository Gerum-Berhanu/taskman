"""Application-level exceptions (mapped to HTTP in the API layer)."""

from starlette.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND


class AppError(Exception):
    status_code: int = 500
    detail: str = "Internal server error"


class EmailAlreadyRegisteredError(AppError):
    status_code = HTTP_400_BAD_REQUEST
    detail = "Account with this email already exists"


class TaskNotFoundError(AppError):
    status_code = HTTP_404_NOT_FOUND
    detail = "Task not found"
