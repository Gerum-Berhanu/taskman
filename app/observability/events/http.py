"""HTTP log event tags (``app.middleware.*`` / ``app.exceptions.handlers`` → envelope ``http``)."""

HTTP_ACCESS = "http_access"
RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
RATE_LIMIT_BACKEND_ERROR = "rate_limit_backend_error"
APP_ERROR = "app_error"
UNHANDLED_ERROR = "unhandled_error"
VALIDATION_ERROR = "validation_error"
