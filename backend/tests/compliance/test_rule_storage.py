"""Phase 6: rule storage, versioning and seed safety. No compliance engine."""

from datetime import date

import pytest

from app.compliance.applicability import is_authoritative, is_effective_on, matches_category
from app.core.enums import RuleStatus, VerificationStatus
from app.schemas.legal_rule import LegalRuleCreate, LegalRuleRecord
from seeds.legal_rules import load_rule_payloads


def test_create_legal_rule_record() -> None:
    rule = LegalRuleCreate(
        rule_code="LM-PC-MRP-001",
        rule_name="Retail sale price",
        description="Declare retail sale price.",
        requirement="Declare the retail sale price of the package.",
        category="PACKAGED_COMMODITY",
        validation_type="MRP_VALIDATION",
        source_document="Legal Metrology (Packaged Commodities) Rules, 2011",
        source_reference="Rule 6(1)(e)",
        source_version="2011",
        effective_from=date(2011, 4, 1),
        rule_status=RuleStatus.ACTIVE,
        verification_status=VerificationStatus.VERIFIED,
    )

    stored = LegalRuleRecord.model_validate(rule.model_dump())
    assert stored.rule_code == "LM-PC-MRP-001"
    assert stored.source_reference == "Rule 6(1)(e)"


def test_retrieve_seed_rule_by_code() -> None:
    mrp = next(item for item in load_rule_payloads() if item.rule_code == "LM-PC-MRP-001")

    assert mrp.rule_name == "Retail sale price"
    assert mrp.source_reference == "Rule 6(1)(e)"


def test_retrieve_rules_by_category() -> None:
    food = [item for item in load_rule_payloads() if matches_category(item.category, item.applicability_condition, "PACKAGED_FOOD")]
    food_codes = {item.rule_code for item in food}

    assert "LM-PC-NETQ-001" in food_codes
    assert "LM-PC-MFR-001" not in food_codes
    assert "LM-PC-DATE-001" not in food_codes


def test_retrieve_rules_by_effective_date() -> None:
    current = LegalRuleCreate(
        rule_code="TEST-DATE-001",
        rule_name="Historic then current",
        description="Fixture only.",
        requirement="Fixture only.",
        category="PACKAGED_COMMODITY",
        validation_type="REQUIRED_DECLARATION",
        source_document="TEST",
        source_version="2011",
        effective_from=date(2011, 4, 1),
        effective_to=date(2022, 12, 31),
        rule_status=RuleStatus.RETIRED,
        verification_status=VerificationStatus.VERIFIED,
    )
    amendment = current.model_copy(
        update={
            "source_version": "2011-amended-2023",
            "effective_from": date(2023, 1, 1),
            "effective_to": None,
            "rule_status": RuleStatus.ACTIVE,
        }
    )

    in_2023 = [
        item
        for item in (current, amendment)
        if is_effective_on(item.effective_from, item.effective_to, date(2023, 6, 1))
    ]

    assert [item.source_version for item in in_2023] == ["2011-amended-2023"]


def test_expired_rule_is_not_currently_active() -> None:
    assert is_effective_on(date(2011, 4, 1), date(2020, 12, 31), date(2026, 8, 23)) is False


def test_future_rule_is_not_returned_for_earlier_date() -> None:
    assert is_effective_on(date(2017, 6, 23), None, date(2015, 1, 1)) is False


def test_duplicate_seed_payloads_are_unique_and_stable() -> None:
    first = load_rule_payloads()
    second = load_rule_payloads()
    keys = [(item.rule_code, item.source_version, item.effective_from) for item in first]

    assert keys == [(item.rule_code, item.source_version, item.effective_from) for item in second]
    assert len(keys) == len(set(keys))


def test_unverified_rule_is_stored_but_not_authoritative() -> None:
    origin = next(item for item in load_rule_payloads() if item.rule_code == "LM-PC-ORIGIN-001")

    assert origin.verification_status is VerificationStatus.UNVERIFIED
    assert origin.rule_status is RuleStatus.DRAFT
    assert origin.source_reference is None
    assert is_authoritative(origin.rule_status, origin.verification_status) is False


def test_verified_seed_rules_cite_rule_6() -> None:
    verified = [item for item in load_rule_payloads() if item.verification_status is VerificationStatus.VERIFIED]

    assert len(verified) == 7
    assert all(item.source_reference and item.source_reference.startswith("Rule 6") for item in verified)
    assert all(item.severity == "UNSPECIFIED" for item in verified)
    assert all(item.effective_from == date(2011, 4, 1) for item in verified)
