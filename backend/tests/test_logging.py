"""Phase 2: request logs include duration; secrets never appear in the line."""

import logging

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.logging_config import configure_logging, get_logger, redact_secrets
from app.main import create_app


def test_redact_secrets_masks_assignment_values() -> None:
    text = "DATABASE_URL=postgres://user:hunter2@localhost/db token=abc123 Authorization: Bearer xyz"

    redacted = redact_secrets(text)

    assert "hunter2" not in redacted
    assert "abc123" not in redacted
    assert "xyz" not in redacted
    assert "DATABASE_URL=[REDACTED]" in redacted
    assert "[REDACTED]" in redacted


def test_logger_filter_redacts_message_arguments(caplog) -> None:
    settings = Settings(log_level="INFO")
    configure_logging(settings)
    logger = get_logger("secrets")
    logger.addHandler(caplog.handler)

    with caplog.at_level(logging.INFO, logger="labelguard"):
        logger.info("connecting with password=%s", "never-log-this")

    assert "never-log-this" not in caplog.text
    assert "[REDACTED]" in caplog.text


def test_request_log_includes_method_path_status_and_duration(caplog) -> None:
    app = create_app(Settings(app_env="development", log_level="INFO"))
    logging.getLogger("labelguard.http").addHandler(caplog.handler)
    client = TestClient(app)

    with caplog.at_level(logging.INFO, logger="labelguard.http"):
        client.get("/health")

    matching = [record.getMessage() for record in caplog.records if "path=/health" in record.getMessage()]

    assert matching
    line = matching[-1]
    assert "stage=http" in line
    assert "method=GET" in line
    assert "status=200" in line
    assert "duration_ms=" in line
    assert "request_id=" in line
    assert "?" not in line
