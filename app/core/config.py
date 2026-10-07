"""Application settings (loaded from environment)."""

from enum import StrEnum
import os
from typing import TypedDict

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnv(StrEnum):
    """Deployed application environment names."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    TEST = "test"
    PRODUCTION = "production"


class FastAPIDocsKwargs(TypedDict, total=False):
    """Optional FastAPI constructor kwargs that control docs/OpenAPI routes."""

    docs_url: str | None
    redoc_url: str | None
    openapi_url: str | None


def _resolve_app_env() -> AppEnv:
    """Resolve TASKMAN_ENV into an AppEnv, defaulting to development."""
    raw = os.getenv("TASKMAN_ENV", AppEnv.DEVELOPMENT.value)
    try:
        return AppEnv(raw)
    except ValueError:
        allowed = ", ".join(e.value for e in AppEnv)
        raise ValueError(
            f"Invalid TASKMAN_ENV={raw!r}; expected one of: {allowed}"
        ) from None


_APP_ENV: AppEnv = _resolve_app_env()


class Settings(BaseSettings):
    """Process env > `env/.env.{TASKMAN_ENV}` > `env/.env` > field defaults."""

    model_config = SettingsConfigDict(
        env_file=("env/.env", f"env/.env.{_APP_ENV.value}"),
        extra="ignore",
    )

    app_name: str = "Taskman"
    app_env: AppEnv = _APP_ENV
    debug: bool = False
    secret_key: str = ""
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 5
    refresh_token_expire_minutes: int = 10_080  # 7 days
    database_url: str = "sqlite+aiosqlite:///./database.db"
    redis_url: str = "redis://127.0.0.1:6379/0"
    log_level: str = "INFO"
    log_json: bool = False
    log_file: bool = True
    rate_limit_enabled: bool = True
    rate_limit_auth_requests: int = 5
    rate_limit_auth_window_seconds: int = 60
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60
    email_enabled: bool = False
    resend_api_key: str = ""
    resend_from: str = "onboarding@resend.dev"
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    email_from: str = ""
    task_summary_cache_ttl_seconds: int = 300 # 5 minutes

    @field_validator("secret_key")
    @classmethod
    def secret_key_must_be_set(cls, value: str) -> str:
        if not value:
            raise ValueError("SECRET_KEY must be set in environment or .env file")
        return value

    @property
    def docs_kwargs(self) -> FastAPIDocsKwargs:
        """FastAPI docs/OpenAPI URLs; empty in development (framework defaults)."""
        if self.app_env == AppEnv.DEVELOPMENT:
            return {}
        return {"docs_url": None, "redoc_url": None, "openapi_url": None}


settings = Settings()
