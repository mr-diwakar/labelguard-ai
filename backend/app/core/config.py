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

    # --- Phase 12: scan intake / image quality / OCR ---
    # All thresholds are configurable because the right value depends on the
    # capture device and label size; the defaults below suit a typical phone
    # photo of a package. None of these are legal thresholds.

    # Intake limits. 10 MiB comfortably holds a high-resolution phone photo while
    # bounding memory for a student laptop.
    scan_max_file_bytes: int = Field(default=10 * 1024 * 1024, ge=1)
    scan_supported_formats: list[str] = Field(default_factory=lambda: ["JPEG", "PNG", "WEBP"])

    # Sanity bounds on decoded dimensions. The upper bound rejects decompression
    # bombs / absurd inputs before any heavy processing.
    image_min_width: int = Field(default=320, ge=1)
    image_min_height: int = Field(default=320, ge=1)
    image_max_width: int = Field(default=12000, ge=1)
    image_max_height: int = Field(default=12000, ge=1)

    # Blur: variance of the Laplacian. Sharp images have high edge energy and
    # therefore high variance; a blurred image smooths edges away and the
    # variance drops. Below this value the image is flagged blurry. ~100 is a
    # widely used starting point for document photos and is intentionally tunable.
    image_blur_threshold: float = Field(default=100.0, ge=0)

    # Brightness: mean of the grayscale image on a 0..255 scale.
    image_brightness_min: float = Field(default=40.0, ge=0, le=255)
    image_brightness_max: float = Field(default=220.0, ge=0, le=255)

    # Preprocessing: cap the long edge fed to OCR so a 4000px photo is downscaled
    # once instead of costing time and memory on every run.
    image_preprocess_max_dim: int = Field(default=2000, ge=1)

    # OCR languages, in priority order. "en" is always safe; "hi" (Hindi) is
    # enabled where the selected PaddleOCR model supports it. Extensible later.
    ocr_languages: list[str] = Field(default_factory=lambda: ["en"])

    # OCR regions at or below this mean confidence flag the result LOW_CONFIDENCE.
    ocr_low_confidence_threshold: float = Field(default=0.5, ge=0, le=1)

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

    @field_validator("scan_supported_formats", "ocr_languages", mode="before")
    @classmethod
    def _parse_csv_list(cls, value: object) -> object:
        """Accepts a comma-separated string for list settings set via .env."""
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]

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
