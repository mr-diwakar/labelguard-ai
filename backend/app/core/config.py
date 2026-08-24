"""Application configuration, read from the environment."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]

API_V1_PREFIX = "/api/v1"


class Settings(BaseSettings):
    """
    Values come from environment variables, falling back to backend/.env and
    then to the defaults below. Later phases add their own fields here rather
    than reading os.environ directly.
    """

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "LabelGuard AI"
    app_env: Literal["development", "staging", "production"] = "development"

    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)

    cors_origins: list[str] = Field(default_factory=list)

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    database_url: SecretStr = SecretStr(
        "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/labelguard"
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors_origins(cls, value: object) -> object:
        """Accepts a comma-separated string so .env stays readable."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]

        return value

    @field_validator("database_url", mode="before")
    @classmethod
    def _normalize_database_url(cls, value: object) -> object:
        """
        PostgreSQL only. A bare postgresql:// URL is rewritten to the psycopg
        driver so SQLAlchemy 2 does not pick an uninstalled adapter.
        """
        if not isinstance(value, str):
            return value

        url = value.strip()
        if url.startswith("postgresql://"):
            return "postgresql+psycopg://" + url[len("postgresql://") :]

        if not url.startswith("postgresql+psycopg://"):
            raise ValueError("DATABASE_URL must be a PostgreSQL URL (postgresql+psycopg://...).")

        return url

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def database_url_value(self) -> str:
        """Raw DSN for SQLAlchemy and Alembic. Do not log this value."""
        return self.database_url.get_secret_value()


@lru_cache
def get_settings() -> Settings:
    """Cached so the environment is parsed once per process."""
    return Settings()
