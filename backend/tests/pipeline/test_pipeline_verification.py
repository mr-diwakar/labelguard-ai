"""Phase 17: label-to-product verification (declared vs visible-in-image).

Asserts the comparison maps onto the existing VerificationOutcome vocabulary and honours
every constraint: image degradation never fabricates a mismatch, no fraud language, no
invented tolerance, and the physical-quantity limitation is always communicated.
"""

from app.core.enums import ObservationSource, VerificationOutcome
from app.pipeline import measured_value_from_text, verify, verify_one
from app.schemas.contracts.verification import (
    MeasuredValue,
    VerificationInput,
    VerificationResult,
)

_FORBIDDEN_WORDS = ("fraud", "counterfeit", "illegal", "cheating", "criminal", "fake")


def _input(field, expected, observed, *, e_unit=None, o_unit=None, confidence=0.9):
    return VerificationInput(
        field=field,
        expected=MeasuredValue(value=expected, unit=e_unit),
        observed=None if observed is None else MeasuredValue(value=observed, unit=o_unit),
        observation_confidence=confidence,
        observation_source=None if observed is None else ObservationSource.OTHER,
    )


# --------------------------------------------------------------------------- #
# Core outcomes
# --------------------------------------------------------------------------- #


def test_equal_printed_values_match():
    result = verify_one(_input("net_quantity", 500, 500, e_unit="g", o_unit="g"))
    assert result.status is VerificationOutcome.MATCH
    assert result.difference == 0.0


def test_differing_confident_values_are_possible_difference_not_fraud():
    result = verify_one(_input("net_quantity", 500, 450, e_unit="g", o_unit="g"))
    assert result.status is VerificationOutcome.POTENTIAL_MISMATCH
    assert result.difference == -50.0
    assert "not a determination of wrongdoing" in result.note
    assert not any(word in result.note.lower() for word in _FORBIDDEN_WORDS)


def test_comparable_units_are_reconciled_before_comparison():
    # 0.5 kg observed vs 500 g declared is a MATCH, not a mismatch.
    result = verify_one(_input("net_quantity", 500, 0.5, e_unit="g", o_unit="kg"))
    assert result.status is VerificationOutcome.MATCH


def test_mrp_difference_reported_without_physical_note():
    result = verify_one(_input("mrp", 50, 60, e_unit="INR", o_unit="INR"))
    assert result.status is VerificationOutcome.POTENTIAL_MISMATCH
    assert result.difference == 10.0
    assert "calibrated measurement" not in (result.note or "")


# --------------------------------------------------------------------------- #
# Image conditions must NOT create a mismatch
# --------------------------------------------------------------------------- #


def test_low_observation_confidence_is_could_not_verify_not_mismatch():
    # A blurred / distant / rotated capture yields a low-confidence reading. Even though
    # the numbers differ, the layer must NOT assert a difference.
    result = verify_one(_input("net_quantity", 500, 450, e_unit="g", o_unit="g", confidence=0.3))
    assert result.status is VerificationOutcome.COULD_NOT_VERIFY
    assert result.method == "insufficient_image"


def test_no_observation_is_could_not_verify():
    result = verify_one(_input("net_quantity", 500, None, e_unit="g"))
    assert result.status is VerificationOutcome.COULD_NOT_VERIFY
    assert result.method == "no_observation"


def test_incomparable_units_are_manual_review():
    result = verify_one(_input("net_quantity", 500, 500, e_unit="g", o_unit="ml"))
    assert result.status is VerificationOutcome.MANUAL_REVIEW
    assert result.method == "uncertain_units"


# --------------------------------------------------------------------------- #
# Physical-quantity limitation is always communicated
# --------------------------------------------------------------------------- #


def test_physical_quantity_limitation_is_stated_for_quantity_fields():
    for observed in (500, 450):  # match and mismatch both carry the caveat
        result = verify_one(_input("net_quantity", 500, observed, e_unit="g", o_unit="g"))
        assert "cannot measure the actual physical weight or volume" in result.note


def test_never_emits_fraud_language_across_outcomes():
    inputs = [
        _input("net_quantity", 500, 500, e_unit="g", o_unit="g"),
        _input("net_quantity", 500, 450, e_unit="g", o_unit="g"),
        _input("net_quantity", 500, None, e_unit="g"),
        _input("net_quantity", 500, 450, e_unit="g", o_unit="g", confidence=0.2),
        _input("mrp", 50, 60, e_unit="INR", o_unit="INR"),
    ]
    for result in verify(inputs):
        assert isinstance(result, VerificationResult)
        assert result.status in set(VerificationOutcome)
        assert not any(word in (result.note or "").lower() for word in _FORBIDDEN_WORDS)


# --------------------------------------------------------------------------- #
# Extraction bridge + determinism
# --------------------------------------------------------------------------- #


def test_measured_value_from_text_parses_number_and_unit():
    assert measured_value_from_text("500 g", "g") == MeasuredValue(value=500.0, unit="g")
    assert measured_value_from_text("50", "INR") == MeasuredValue(value=50.0, unit="INR")
    # unit inferred from trailing token when not supplied
    assert measured_value_from_text("250 ml") == MeasuredValue(value=250.0, unit="ml")
    # non-numeric text is not verifiable on this numeric contract
    assert measured_value_from_text("India") is None
    assert measured_value_from_text(None) is None


def test_verify_is_deterministic_and_order_preserving():
    inputs = [
        _input("mrp", 50, 50, e_unit="INR", o_unit="INR"),
        _input("net_quantity", 500, 400, e_unit="g", o_unit="g"),
    ]
    first = [r.model_dump() for r in verify(inputs)]
    second = [r.model_dump() for r in verify(inputs)]
    assert first == second
    assert [r["field"] for r in first] == ["mrp", "net_quantity"]
