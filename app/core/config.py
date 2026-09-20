"""Application settings (loaded from environment)."""

from enum import StrEnum
import os

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnv(StrEnum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"


def _resolve_app_env() -> AppEnv:
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
    debug: bool = False
    secret_key: str = ""
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 5
    refresh_token_expire_minutes: int = 10_080  # 7 days
    database_url: str = "sqlite+aiosqlite:///./database.db"

    @field_validator("secret_key")
    @classmethod
    def secret_key_must_be_set(cls, value: str) -> str:
        if not value:
            raise ValueError("SECRET_KEY must be set in environment or .env file")
        return value


settings = Settings()
