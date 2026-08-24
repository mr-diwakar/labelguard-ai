"""Process-wide logging. Secrets are redacted before a line is emitted."""

import logging
import re

from app.core.config import Settings

LOGGER_NAME = "labelguard"

# Field names and common env-style keys that must never appear in logs.
_SENSITIVE_NAMES = (
    "password",
    "passwd",
    "secret",
    "token",
    "authorization",
    "api_key",
    "apikey",
    "access_key",
    "database_url",
    "db_url",
)

_REDACTED = "[REDACTED]"

# Matches password=foo, token: bar, DATABASE_URL=postgres://...
_SENSITIVE_ASSIGNMENT = re.compile(
    r"(?i)\b(" + "|".join(re.escape(name) for name in _SENSITIVE_NAMES) + r")\b(\s*[=:]\s*)(.+)"
)


def redact_secrets(text: str) -> str:
    """Replaces secret values while leaving the field name visible for debugging."""
    return _SENSITIVE_ASSIGNMENT.sub(rf"\1\2{_REDACTED}", text)


class SecretRedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            rendered = record.getMessage()
        except Exception:
            rendered = str(record.msg)

        record.msg = redact_secrets(rendered)
        record.args = ()
        return True


def configure_logging(settings: Settings) -> None:
    """
    Installs the LabelGuard logger once per process.

    Existing handlers are replaced so tests and reloads do not stack duplicates.
    Uvicorn keeps its own loggers; we only own application records.
    """
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(settings.log_level)
    logger.propagate = False

    for existing_filter in list(logger.filters):
        logger.removeFilter(existing_filter)
    logger.addFilter(SecretRedactingFilter())

    for handler in list(logger.handlers):
        logger.removeHandler(handler)

    handler = logging.StreamHandler()
    handler.setLevel(settings.log_level)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s", datefmt="%Y-%m-%dT%H:%M:%S")
    )
    logger.addHandler(handler)


def get_logger(name: str | None = None) -> logging.Logger:
    logger = logging.getLogger(f"{LOGGER_NAME}.{name}") if name else logging.getLogger(LOGGER_NAME)
    if not any(isinstance(item, SecretRedactingFilter) for item in logger.filters):
        logger.addFilter(SecretRedactingFilter())
    return logger
