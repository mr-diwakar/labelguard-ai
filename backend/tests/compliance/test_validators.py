"""Phase 8: one validator, one requirement. No overall inspection status."""

from datetime import date

from app.compliance.registry import build_default_registry
from app.compliance.validators.consumer_care import ConsumerCareValidator
from app.compliance.validators.date_declaration import DateDeclarationValidator
from app.compliance.validators.mrp import MRPValidator
from app.compliance.validators.net_quantity import NetQuantityValidator
from app.compliance.validators.required import RequiredDeclarationValidator
from app.core.enums import (
    DeclarationStatus,
    RuleStatus,
    ValidationOutcome,
    ValidationType,
    VerificationStatus,
)
from app.schemas.declaration import Declaration
from app.schemas.legal_rule import LegalRuleRecord
from app.schemas.validation import ValidationContext
from seeds.legal_rules import load_rule_payloads


def _seed(rule_code: str) -> LegalRuleRecord:
    for item in load_rule_payloads():
        if item.rule_code == rule_code:
            return LegalRuleRecord.model_validate(item.model_dump())
    raise AssertionError(rule_code)


def _declaration(
    field: str,
    value: str | None,
    *,
    status: str = "DETECTED",
    confidence: float | None = 0.98,
    bbox: list[int] | None = None,
) -> Declaration:
    return Declaration.model_validate(
        {
            "field": field,
            "value": value,
            "confidence": confidence,
            "source": "OCR",
            "bbox": bbox or [100, 200, 300, 250],
            "status": status,
        }
    )


def _context(**overrides) -> ValidationContext:
    payload = {"category": "HOUSEHOLD_PRODUCT", "applicable": True}
    payload.update(overrides)
    return ValidationContext.model_validate(payload)


def _care_rule() -> LegalRuleRecord:
    base = _seed("LM-PC-CARE-001").model_dump()
    base["validation_type"] = ValidationType.CONSUMER_CARE_VALIDATION
    return LegalRuleRecord.model_validate(base)


def test_required_declaration_detected_is_pass() -> None:
    result = RequiredDeclarationValidator().validate(
        _seed("LM-PC-NAME-001"),
        [_declaration("commodity_name", "Bath soap")],
        _context(),
    )

    assert result.result is ValidationOutcome.PASS
    assert result.rule_code == "LM-PC-NAME-001"
    assert result.source_reference == "Rule 6(1)(b)"
    assert result.evidence[0].bbox == [100, 200, 300, 250]
    assert result.confidence != 0.98


def test_required_declaration_reliable_absence_is_potential_non_compliance() -> None:
    result = RequiredDeclarationValidator().validate(
        _seed("LM-PC-NAME-001"),
        [_declaration("commodity_name", None, status="NOT_DETECTED", confidence=0.92)],
        _context(label_readable=True),
    )

    assert result.result is ValidationOutcome.POTENTIAL_NON_COMPLIANCE


def test_required_declaration_low_confidence_not_detected_is_manual_review() -> None:
    result = RequiredDeclarationValidator().validate(
        _seed("LM-PC-NAME-001"),
        [_declaration("commodity_name", None, status="NOT_DETECTED", confidence=0.40)],
        _context(),
    )

    assert result.result is ValidationOutcome.MANUAL_REVIEW
    assert result.result is not ValidationOutcome.POTENTIAL_NON_COMPLIANCE


def test_required_declaration_not_applicable_for_food_manufacturer_rule() -> None:
    result = RequiredDeclarationValidator().validate(
        _seed("LM-PC-MFR-001"),
        [_declaration("manufacturer", "Acme Foods")],
        ValidationContext(category="PACKAGED_FOOD"),
    )

    assert result.result is ValidationOutcome.NOT_APPLICABLE


def test_mrp_numeric_and_rupee_prefix_pass() -> None:
    validator = MRPValidator()
    rule = _seed("LM-PC-MRP-001")

    numeric = validator.validate(rule, [_declaration("mrp", "50")], _context())
    rupee = validator.validate(rule, [_declaration("mrp", "₹50")], _context())

    assert numeric.result is ValidationOutcome.PASS
    assert rupee.result is ValidationOutcome.PASS
    assert "parsed successfully" in rupee.reason


def test_mrp_negative_and_malformed_are_potential_non_compliance() -> None:
    validator = MRPValidator()
    rule = _seed("LM-PC-MRP-001")

    negative = validator.validate(rule, [_declaration("mrp", "-50")], _context())
    malformed = validator.validate(rule, [_declaration("mrp", "ABC")], _context())

    assert negative.result is ValidationOutcome.POTENTIAL_NON_COMPLIANCE
    assert malformed.result is ValidationOutcome.POTENTIAL_NON_COMPLIANCE


def test_mrp_not_detected_low_confidence_is_manual_review() -> None:
    result = MRPValidator().validate(
        _seed("LM-PC-MRP-001"),
        [_declaration("mrp", None, status="NOT_DETECTED", confidence=0.40)],
        _context(),
    )

    assert result.result is ValidationOutcome.MANUAL_REVIEW
    assert result.result is not ValidationOutcome.POTENTIAL_NON_COMPLIANCE


def test_manually_verified_negative_mrp_is_still_checked() -> None:
    result = MRPValidator().validate(
        _seed("LM-PC-MRP-001"),
        [_declaration("mrp", "-50", status="MANUALLY_VERIFIED", confidence=1.0)],
        _context(),
    )

    assert result.result is ValidationOutcome.POTENTIAL_NON_COMPLIANCE


def test_net_quantity_valid_units_pass() -> None:
    validator = NetQuantityValidator()
    rule = _seed("LM-PC-NETQ-001")

    grams = validator.validate(rule, [_declaration("net_quantity", "100 g")], _context())
    millilitres = validator.validate(rule, [_declaration("net_quantity", "500 ml")], _context())

    assert grams.result is ValidationOutcome.PASS
    assert millilitres.result is ValidationOutcome.PASS


def test_net_quantity_zero_negative_and_invalid_are_potential_non_compliance() -> None:
    validator = NetQuantityValidator()
    rule = _seed("LM-PC-NETQ-001")

    zero = validator.validate(rule, [_declaration("net_quantity", "0 g")], _context())
    negative = validator.validate(rule, [_declaration("net_quantity", "-10 g")], _context())
    invalid = validator.validate(rule, [_declaration("net_quantity", "abc g")], _context())

    assert zero.result is ValidationOutcome.POTENTIAL_NON_COMPLIANCE
    assert negative.result is ValidationOutcome.POTENTIAL_NON_COMPLIANCE
    assert invalid.result is ValidationOutcome.POTENTIAL_NON_COMPLIANCE


def test_net_quantity_ocr_uncertainty_is_manual_review() -> None:
    result = NetQuantityValidator().validate(
        _seed("LM-PC-NETQ-001"),
        [_declaration("net_quantity", None, status="NOT_DETECTED", confidence=0.40)],
        _context(),
    )

    assert result.result is ValidationOutcome.MANUAL_REVIEW


def test_date_valid_representations_pass() -> None:
    validator = DateDeclarationValidator()
    rule = _seed("LM-PC-DATE-001")

    for value in ("07/2026", "2026-07", "2026-07-15"):
        result = validator.validate(rule, [_declaration("manufacture_date", value)], _context())
        assert result.result is ValidationOutcome.PASS, value


def test_date_impossible_and_malformed_are_potential_non_compliance() -> None:
    validator = DateDeclarationValidator()
    rule = _seed("LM-PC-DATE-001")

    impossible = validator.validate(rule, [_declaration("date", "2026-02-30")], _context())
    malformed = validator.validate(rule, [_declaration("date", "not-a-date")], _context())

    assert impossible.result is ValidationOutcome.POTENTIAL_NON_COMPLIANCE
    assert malformed.result is ValidationOutcome.POTENTIAL_NON_COMPLIANCE


def test_date_unreadable_is_manual_review() -> None:
    result = DateDeclarationValidator().validate(
        _seed("LM-PC-DATE-001"),
        [_declaration("date", None, status="NOT_DETECTED", confidence=0.40)],
        _context(),
    )

    assert result.result is ValidationOutcome.MANUAL_REVIEW


def test_consumer_care_detected_pass_and_malformed_fail() -> None:
    validator = ConsumerCareValidator()
    rule = _care_rule()

    detected = validator.validate(
        rule,
        [_declaration("consumer_care", "Acme Care, 1800123456, care@acme.test")],
        _context(),
    )
    malformed = validator.validate(rule, [_declaration("consumer_care", "???")], _context())

    assert detected.result is ValidationOutcome.PASS
    assert malformed.result is ValidationOutcome.POTENTIAL_NON_COMPLIANCE


def test_consumer_care_low_confidence_is_manual_review() -> None:
    result = ConsumerCareValidator().validate(
        _care_rule(),
        [_declaration("consumer_care", None, status="NOT_DETECTED", confidence=0.40)],
        _context(),
    )

    assert result.result is ValidationOutcome.MANUAL_REVIEW


def test_low_confidence_not_detected_never_becomes_a_violation() -> None:
    result = MRPValidator().validate(
        _seed("LM-PC-MRP-001"),
        [_declaration("mrp", None, status="NOT_DETECTED", confidence=0.40)],
        _context(label_readable=True),
    )

    assert result.result is ValidationOutcome.MANUAL_REVIEW
    assert result.result is not ValidationOutcome.POTENTIAL_NON_COMPLIANCE


def test_unverified_rule_is_not_treated_as_production_law() -> None:
    result = RequiredDeclarationValidator().validate(
        _seed("LM-PC-ORIGIN-001"),
        [_declaration("country_of_origin", "India")],
        _context(category="IMPORTED_PRODUCT", is_imported=True, applicable=True),
    )

    assert result.result is ValidationOutcome.MANUAL_REVIEW
    assert _seed("LM-PC-ORIGIN-001").rule_status is RuleStatus.DRAFT
    assert _seed("LM-PC-ORIGIN-001").verification_status is VerificationStatus.UNVERIFIED


def test_explicit_not_applicable_context() -> None:
    result = MRPValidator().validate(
        _seed("LM-PC-MRP-001"),
        [_declaration("mrp", "50")],
        _context(applicable=False),
    )

    assert result.result is ValidationOutcome.NOT_APPLICABLE


def test_registry_maps_seed_validation_types() -> None:
    registry = build_default_registry()

    assert isinstance(registry.resolve(ValidationType.REQUIRED_DECLARATION), RequiredDeclarationValidator)
    assert isinstance(registry.resolve(ValidationType.MRP_VALIDATION), MRPValidator)
    assert isinstance(registry.resolve(ValidationType.NET_QUANTITY_VALIDATION), NetQuantityValidator)
    assert isinstance(registry.resolve(ValidationType.DATE_VALIDATION), DateDeclarationValidator)
    assert isinstance(registry.resolve(ValidationType.CONSUMER_CARE_VALIDATION), ConsumerCareValidator)
    assert registry.get(ValidationType.CONDITIONAL_REQUIREMENT) is None


def test_registry_runs_seed_mrp_rule() -> None:
    rule = _seed("LM-PC-MRP-001")
    validator = build_default_registry().resolve(rule.validation_type)
    result = validator.validate(rule, [_declaration("mrp", "50")], _context())

    assert result.result is ValidationOutcome.PASS
    assert result.severity.value == "UNSPECIFIED"


def test_declaration_status_enum_has_no_missing() -> None:
    assert "MISSING" not in DeclarationStatus.__members__


def test_validation_uses_inspection_date_context_without_loading_latest_rule() -> None:
    result = DateDeclarationValidator().validate(
        _seed("LM-PC-DATE-001"),
        [_declaration("manufacture_date", "07/2026")],
        _context(inspection_date=date(2026, 8, 23)),
    )

    assert result.result is ValidationOutcome.PASS
