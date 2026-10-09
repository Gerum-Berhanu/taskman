"""Registered log event tags (source of truth alongside docs/log-events.md)."""

from enum import StrEnum


class LogEvent(StrEnum):
    """Base for all log event tags. Members live on category subclasses."""


class HttpLogEvent(LogEvent):
    """Tags from ``app.middleware.*`` / ``app.exception_handlers`` → envelope ``http``."""

    HTTP_ACCESS = "http_access"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    RATE_LIMIT_BACKEND_ERROR = "rate_limit_backend_error"
    APP_ERROR = "app_error"
    UNHANDLED_ERROR = "unhandled_error"


class InfraLogEvent(LogEvent):
    """Tags from ``app.infrastructure.*`` → envelope ``infra``."""

    REDIS_UNAVAILABLE_AT_STARTUP = "redis_unavailable_at_startup"
    EMAIL_SENT = "email_sent"
    EMAIL_SEND_FAILED = "email_send_failed"
    EMAIL_SKIPPED = "email_skipped"
    TASK_EXPORT_SENT = "task_export_sent"
    TASK_EXPORT_FAILED = "task_export_failed"


class OpsLogEvent(LogEvent):
    """Tags from ``app.repositories.*`` → envelope ``ops``."""

    AFTER_COMMIT_FAILED = "after_commit_failed"


class DomainLogEvent(LogEvent):
    """Tags from ``app.services.*`` → envelope ``domain``."""

    USER_REGISTERED = "user_registered"
    USER_LOGIN_SUCCEEDED = "user_login_succeeded"
    USER_LOGOUT = "user_logout"
    USER_LOGOUT_ALL = "user_logout_all"
    WORKSPACE_CREATED = "workspace_created"
    WORKSPACE_MEMBER_ADDED = "workspace_member_added"
    TASK_CREATED = "task_created"
    TASK_UPDATED = "task_updated"
    TASK_DELETED = "task_deleted"
    CACHE_BACKEND_ERROR = "cache_backend_error"
