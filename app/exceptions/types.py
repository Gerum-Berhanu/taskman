"""Application-level exceptions (mapped to HTTP in the API layer)."""

from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
    HTTP_429_TOO_MANY_REQUESTS,
    HTTP_503_SERVICE_UNAVAILABLE,
)


class AppError(Exception):
    """Base domain error carrying HTTP status, detail, and optional headers."""

    status_code: int = 500
    detail: str = "Something went wrong"
    headers: dict[str, str] | None = None


# Auth / session
class EmailAlreadyRegisteredError(AppError):
    status_code = HTTP_409_CONFLICT
    detail = "Account with this email already exists"


class InvalidCredentialsError(AppError):
    status_code = HTTP_401_UNAUTHORIZED
    detail = "Incorrect email or password"
    headers = {"WWW-Authenticate": "Bearer"}


class InvalidTokenError(AppError):
    status_code = HTTP_401_UNAUTHORIZED
    detail = "Could not validate credentials"
    headers = {"WWW-Authenticate": "Bearer"}


class SessionNotFoundError(AppError):
    status_code = HTTP_404_NOT_FOUND
    detail = "Session not found"


class UserNotFoundError(AppError):
    status_code = HTTP_404_NOT_FOUND
    detail = "User not found"


# Workspace / tasks
class AssigneeNotInWorkspaceError(AppError):
    status_code = HTTP_400_BAD_REQUEST
    detail = "Assignee is not a member of the workspace"


class MembershipAlreadyExistsError(AppError):
    status_code = HTTP_409_CONFLICT
    detail = "Member is already in the workspace"


class TaskNotFoundError(AppError):
    status_code = HTTP_404_NOT_FOUND
    detail = "Task not found"


class WorkspaceForbiddenError(AppError):
    status_code = HTTP_403_FORBIDDEN
    detail = "Insufficient workspace permissions"


# Registration OTP
class InvalidEmailDomainError(AppError):
    status_code = HTTP_400_BAD_REQUEST
    detail = "Email domain is not allowed"


class RegistrationOtpAttemptsExceededError(AppError):
    status_code = HTTP_400_BAD_REQUEST
    detail = "Registration attempts exceeded"


class RegistrationOtpInvalidError(AppError):
    status_code = HTTP_400_BAD_REQUEST
    detail = "Invalid or expired registration code"


# Infra availability
class ServiceUnavailableError(AppError):
    status_code = HTTP_503_SERVICE_UNAVAILABLE
    detail = "Service temporarily unavailable"


# Request gating
class RateLimitExceededError(AppError):
    status_code = HTTP_429_TOO_MANY_REQUESTS
    detail = "Too many requests"

    def __init__(self, retry_after: int | float | None = None) -> None:
        if retry_after is not None:
            self.headers = {"Retry-After": str(round(retry_after, 2))}


class UnknownClientError(AppError):
    status_code = HTTP_400_BAD_REQUEST
    detail = "Unknown client address"
