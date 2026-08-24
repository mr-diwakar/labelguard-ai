"""In-memory rule fixtures. These are not official Legal Metrology text."""

from datetime import date

from app.core.enums import RuleStatus, VerificationStatus
from app.schemas.legal_rule import LegalRuleRecord
from seeds.legal_rules import load_rule_payloads


def fixture_rule(**overrides) -> LegalRuleRecord:
    base = dict(
        rule_code="TEST-FIX-001",
        rule_name="Fixture requirement",
        description="Test fixture. Not a legal requirement.",
        requirement="Fixture only.",
        category="PACKAGED_COMMODITY",
        validation_type="REQUIRED_DECLARATION",
        source_document="TEST",
        source_reference="Fixture",
        source_version="A",
        effective_from=date(2011, 4, 1),
        effective_to=None,
        rule_status=RuleStatus.ACTIVE,
        verification_status=VerificationStatus.VERIFIED,
        applicability_condition={"applies_to_categories": ["*"], "declaration_fields": ["name"]},
    )
    base.update(overrides)
    return LegalRuleRecord.model_validate(base)


def seed_rules() -> list[LegalRuleRecord]:
    return [LegalRuleRecord.model_validate(item.model_dump()) for item in load_rule_payloads()]


def mrp_rule(**overrides) -> LegalRuleRecord:
    payload = dict(
        rule_code="TEST-MRP-001",
        validation_type="MRP_VALIDATION",
        applicability_condition={"applies_to_categories": ["*"], "declaration_fields": ["mrp"]},
    )
    payload.update(overrides)
    return fixture_rule(**payload)


def net_quantity_rule(**overrides) -> LegalRuleRecord:
    payload = dict(
        rule_code="TEST-NETQ-001",
        validation_type="NET_QUANTITY_VALIDATION",
        applicability_condition={"applies_to_categories": ["*"], "declaration_fields": ["net_quantity"]},
    )
    payload.update(overrides)
    return fixture_rule(**payload)


def date_rule(**overrides) -> LegalRuleRecord:
    payload = dict(
        rule_code="TEST-DATE-001",
        validation_type="DATE_VALIDATION",
        applicability_condition={"applies_to_categories": ["*"], "declaration_fields": ["date"]},
    )
    payload.update(overrides)
    return fixture_rule(**payload)


def care_rule(**overrides) -> LegalRuleRecord:
    payload = dict(
        rule_code="TEST-CARE-001",
        validation_type="CONSUMER_CARE_VALIDATION",
        applicability_condition={"applies_to_categories": ["*"], "declaration_fields": ["consumer_care"]},
    )
    payload.update(overrides)
    return fixture_rule(**payload)
