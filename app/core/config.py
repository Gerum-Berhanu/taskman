"""Application settings (loaded from environment)."""

from enum import StrEnum
import os
from typing import Self, TypedDict

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnv(StrEnum):
    """Deployed application environment names."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    TEST = "test"
    PRODUCTION = "production"


class EmailProvider(StrEnum):
    """Outbound mail transport selected by EMAIL_PROVIDER."""

    SMTP = "smtp"
    RESEND = "resend"


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


class AppSettings(BaseSettings):
    """Process identity and FastAPI surface knobs."""

    app_name: str = "Taskman"
    app_env: AppEnv = _APP_ENV
    debug: bool = False

    @property
    def docs_kwargs(self) -> FastAPIDocsKwargs:
        """FastAPI docs/OpenAPI URLs; empty in development (framework defaults)."""
        if self.app_env == AppEnv.DEVELOPMENT:
            return {}
        return {"docs_url": None, "redoc_url": None, "openapi_url": None}


class AuthSettings(BaseSettings):
    """JWT, cookies, and client-session caps."""

    secret_key: str = Field(default="", min_length=32)
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 5
    refresh_token_expire_minutes: int = 10_080  # 7 days
    refresh_token_cookie_name: str = "refresh_token"
    device_id_cookie_name: str = "device_id"
    device_id_cookie_max_age_seconds: int = 34_560_000  # ~400 days
    max_client_sessions_per_user: int = Field(default=15, ge=1)
    session_purge_interval_seconds: int = Field(default=3600, ge=1)


class InfraSettings(BaseSettings):
    """Database, Redis, RabbitMQ, and rate-limit enable flag."""

    database_url: str = "sqlite+aiosqlite:///./database.db"
    redis_cache_url: str = "redis://127.0.0.1:6379/0"
    redis_rate_limit_url: str = "redis://127.0.0.1:6379/1"
    redis_registration_url: str = "redis://127.0.0.1:6379/2"
    rabbitmq_url: str = "amqp://guest:guest@127.0.0.1:5672//"
    rate_limit_enabled: bool = True


class ObservabilitySettings(BaseSettings):
    """Log level and sink format flags."""

    log_level: str = "INFO"
    log_json: bool = False
    log_file: bool = True


class EmailSettings(BaseSettings):
    """Enable flag, From addresses, Resend, and SMTP knobs."""

    email_enabled: bool = False
    email_from: str = ""
    email_provider: EmailProvider = EmailProvider.SMTP
    resend_api_key: str = ""
    resend_from: str = "onboarding@resend.dev"
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""

    @model_validator(mode="after")
    def email_provider_credentials(self) -> Self:
        # When email is on, require credentials for the selected provider.
        if not self.email_enabled:
            return self
        if self.email_provider is EmailProvider.RESEND and not self.resend_api_key:
            raise ValueError(
                "RESEND_API_KEY is required when EMAIL_ENABLED and EMAIL_PROVIDER=resend"
            )
        return self


class FeatureSettings(BaseSettings):
    """Task cache/bulk limits, OTP knobs, and allowed signup domains."""

    task_summary_cache_ttl_seconds: int = 300  # 5 minutes
    task_bulk_max_items: int = Field(default=50, ge=1)
    registration_otp_ttl_seconds: int = Field(default=600, ge=1)  # 10 minutes
    registration_otp_length: int = Field(default=6, ge=4, le=10)
    registration_otp_max_attempts: int = Field(default=5, ge=1)
    allowed_email_domains: frozenset[str] = Field(default_factory=frozenset)

    @field_validator("allowed_email_domains", mode="before")
    @classmethod
    def normalize_allowed_email_domains(cls, value: object) -> frozenset[str]:
        if value is None:
            return frozenset()
        if isinstance(value, (list, tuple, set, frozenset)):
            return frozenset(
                str(part).strip().casefold() for part in value if str(part).strip()
            )
        raise TypeError("allowed_email_domains must be a JSON array of domains")


class Settings(
    AppSettings,
    AuthSettings,
    InfraSettings,
    ObservabilitySettings,
    EmailSettings,
    FeatureSettings,
):
    """Process env > `env/.env.{TASKMAN_ENV}` > `env/.env` > field defaults."""

    model_config = SettingsConfigDict(
        env_file=("env/.env", f"env/.env.{_APP_ENV.value}"),
        extra="ignore",
    )


settings = Settings()
