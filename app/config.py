"""Application settings (loaded from environment)."""

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    secret_key: str = Field(default="")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    @field_validator("secret_key")
    @classmethod
    def secret_key_must_be_set(cls, value: str) -> str:
        if not value:
            raise ValueError("SECRET_KEY must be set in environment or .env file")
        return value


settings = Settings()
