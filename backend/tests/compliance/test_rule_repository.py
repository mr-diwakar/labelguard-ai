"""Persistence tests. Skipped when PostgreSQL is not running."""

from datetime import date

import pytest
from sqlalchemy.orm import Session

from app.compliance.repository import LegalRuleRepository
from app.core.config import Settings
from app.core.enums import RuleStatus, VerificationStatus
from app.database.connection import check_database, create_engine_from_settings, dispose_engine
from app.schemas.legal_rule import LegalRuleCreate
from seeds.legal_rules import seed_legal_rules


def _session() -> Session:
    dispose_engine()
    engine = create_engine_from_settings(Settings())
    if not check_database(engine):
        engine.dispose()
        pytest.skip("PostgreSQL is not running")
    return Session(engine)


@pytest.fixture
def session() -> Session:
    db = _session()
    try:
        yield db
        db.rollback()
    finally:
        db.close()
        dispose_engine()


def _sample(code: str = "TEST-STORE-001") -> LegalRuleCreate:
    return LegalRuleCreate(
        rule_code=code,
        rule_name="Test storage row",
        description="Not a legal requirement.",
        requirement="Used only to prove insert and lookup.",
        category="PACKAGED_COMMODITY",
        validation_type="REQUIRED_DECLARATION",
        source_document="TEST",
        source_reference=None,
        source_version="test",
        effective_from=date(2020, 1, 1),
        rule_status=RuleStatus.ACTIVE,
        verification_status=VerificationStatus.UNVERIFIED,
    )


def test_create_and_get_rule_by_code(session: Session) -> None:
    repository = LegalRuleRepository(session)
    created = repository.create_rule(_sample())
    found = repository.get_rule_by_code("TEST-STORE-001")

    assert created.id is not None
    assert found is not None
    assert found.rule_code == "TEST-STORE-001"


def test_seed_twice_does_not_duplicate(session: Session) -> None:
    first = seed_legal_rules(session)
    session.commit()
    second = seed_legal_rules(session)
    repository = LegalRuleRepository(session)

    assert first["total"] == 8
    assert second["created"] == 0
    assert repository.count_by_code("LM-PC-MRP-001") == 1
