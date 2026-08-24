"""Phase 10: structural edge cases for existing validators. No new legal rules."""

from app.compliance.validators.consumer_care import ConsumerCareValidator
from app.compliance.validators.date_declaration import DateDeclarationValidator
from app.compliance.validators.mrp import MRPValidator
from app.compliance.validators.net_quantity import NetQuantityValidator
from app.core.enums import ValidationOutcome
from app.schemas.validation import ValidationContext
from tests.fixtures.declarations import declaration
from tests.fixtures.rules import care_rule, date_rule, mrp_rule, net_quantity_rule

CONTEXT = ValidationContext(category="HOUSEHOLD_PRODUCT", applicable=True)


def test_mrp_normalized_forms_pass() -> None:
    validator = MRPValidator()
    rule = mrp_rule()

    for value in ("₹50", "50", "MRP ₹50", "₹50.00"):
        result = validator.validate(rule, [declaration("mrp", value)], CONTEXT)
        assert result.result is ValidationOutcome.PASS, value


def test_mrp_negative_and_malformed_fail_when_detected() -> None:
    validator = MRPValidator()
    rule = mrp_rule()

    assert validator.validate(rule, [declaration("mrp", "-50")], CONTEXT).result is ValidationOutcome.POTENTIAL_NON_COMPLIANCE
    assert validator.validate(rule, [declaration("mrp", "ABC")], CONTEXT).result is ValidationOutcome.POTENTIAL_NON_COMPLIANCE


def test_mrp_empty_detected_value_is_manual_review() -> None:
    result = MRPValidator().validate(mrp_rule(), [declaration("mrp", "")], CONTEXT)

    assert result.result is ValidationOutcome.MANUAL_REVIEW


def test_net_quantity_valid_and_invalid() -> None:
    validator = NetQuantityValidator()
    rule = net_quantity_rule()

    for value in ("100 g", "500 ml", "1 kg"):
        assert validator.validate(rule, [declaration("net_quantity", value)], CONTEXT).result is ValidationOutcome.PASS

    for value in ("0 g", "-100 g", "abc g"):
        assert (
            validator.validate(rule, [declaration("net_quantity", value)], CONTEXT).result
            is ValidationOutcome.POTENTIAL_NON_COMPLIANCE
        )


def test_net_quantity_poor_ocr_is_manual_review() -> None:
    result = NetQuantityValidator().validate(
        net_quantity_rule(),
        [declaration("net_quantity", None, status="NOT_DETECTED", confidence=0.35)],
        CONTEXT,
    )

    assert result.result is ValidationOutcome.MANUAL_REVIEW


def test_date_supported_and_impossible_representations() -> None:
    validator = DateDeclarationValidator()
    rule = date_rule()

    for value in ("07/2026", "2026-07", "2026-07-15"):
        assert validator.validate(rule, [declaration("date", value)], CONTEXT).result is ValidationOutcome.PASS

    assert validator.validate(rule, [declaration("date", "32/2026")], CONTEXT).result is ValidationOutcome.POTENTIAL_NON_COMPLIANCE
    assert validator.validate(rule, [declaration("date", "2026-13")], CONTEXT).result is ValidationOutcome.POTENTIAL_NON_COMPLIANCE
    assert validator.validate(rule, [declaration("date", "99/99")], CONTEXT).result is ValidationOutcome.POTENTIAL_NON_COMPLIANCE


def test_consumer_care_valid_malformed_and_uncertain() -> None:
    validator = ConsumerCareValidator()
    rule = care_rule()

    phone = validator.validate(rule, [declaration("consumer_care", "1800123456")], CONTEXT)
    email = validator.validate(rule, [declaration("consumer_care", "care@acme.test")], CONTEXT)
    malformed = validator.validate(rule, [declaration("consumer_care", "???")], CONTEXT)
    uncertain = validator.validate(
        rule,
        [declaration("consumer_care", None, status="NOT_DETECTED", confidence=0.45)],
        CONTEXT,
    )

    assert phone.result is ValidationOutcome.PASS
    assert email.result is ValidationOutcome.PASS
    assert malformed.result is ValidationOutcome.POTENTIAL_NON_COMPLIANCE
    assert uncertain.result is ValidationOutcome.MANUAL_REVIEW
