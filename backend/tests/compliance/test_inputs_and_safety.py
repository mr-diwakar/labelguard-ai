"""Phase 10: malformed input, logging, and local safety checks."""

import inspect
import logging
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.compliance import engine as engine_module
from app.compliance import repository as repository_module
from app.compliance.engine import ComplianceEngine
from app.core.enums import ComplianceStatus
from app.schemas.assessment import ComplianceRequest
from app.schemas.declaration import Declaration
from tests.fixtures.inspections import engine, request
from tests.fixtures.rules import fixture_rule
from tests.fixtures.validators import broken_required_registry


def test_invalid_inspection_date_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ComplianceRequest.model_validate(
            {"inspection_date": "not-a-date", "product_category": "HOUSEHOLD_PRODUCT", "declarations": []}
        )


def test_unknown_category_does_not_become_compliant_without_rules() -> None:
    result = engine([fixture_rule(applicability_condition={"applies_to_categories": ["PACKAGED_FOOD"], "declaration_fields": ["name"]})]).evaluate(
        request(product_category="NOT_A_REAL_CATEGORY")
    )

    assert result.status is ComplianceStatus.MANUAL_REVIEW
    assert result.status is not ComplianceStatus.COMPLIANT


def test_malformed_declaration_and_confidence_are_rejected() -> None:
    with pytest.raises(ValidationError):
        Declaration.model_validate({"field": "mrp", "value": "50"})
    with pytest.raises(ValidationError):
        Declaration.model_validate({"field": "mrp", "status": "DETECTED", "confidence": 1.5})
    with pytest.raises(ValidationError):
        Declaration.model_validate({"field": "mrp", "status": "DETECTED", "confidence": -0.1})
    with pytest.raises(ValidationError):
        Declaration.model_validate({"field": "mrp", "status": "MISSING"})


def test_missing_declarations_do_not_become_compliant() -> None:
    result = engine([fixture_rule()]).evaluate(request(declarations=[]))

    assert result.status is ComplianceStatus.MANUAL_REVIEW


def test_validator_failure_is_logged_without_user_stack_trace(caplog) -> None:
    with caplog.at_level(logging.ERROR, logger="labelguard.compliance"):
        result = engine([fixture_rule()], broken_required_registry()).evaluate(request())

    assert result.status is ComplianceStatus.MANUAL_REVIEW
    assert "stack" not in result.explanation.lower()
    assert "Traceback" not in result.manual_review[0].reason
    assert any("stage=validator" in record.getMessage() for record in caplog.records)


def test_compliance_modules_do_not_build_raw_sql_or_accept_file_paths() -> None:
    engine_src = inspect.getsource(engine_module)
    repo_src = inspect.getsource(repository_module)

    assert "execute(" not in engine_src
    assert "text(" not in repo_src
    assert ".format(" not in repo_src
    assert "f\"SELECT" not in repo_src
    assert "Path(" not in engine_src
    assert "open(" not in engine_src


def test_no_hardcoded_secrets_in_compliance_package() -> None:
    root = Path(__file__).resolve().parents[2] / "app" / "compliance"
    forbidden = ("sk-", "BEGIN PRIVATE KEY", "postgres://postgres:postgres")

    for path in root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, path


def test_engine_has_no_database_import() -> None:
    source = inspect.getsource(ComplianceEngine)
    assert "sqlalchemy" not in source
    assert "Session" not in source
