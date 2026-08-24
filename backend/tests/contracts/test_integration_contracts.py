"""
Phase 11 integration-contract tests.

Two layers are covered:
  * contract shape/validation (no engine): the new schemas accept valid data, reject
    malformed data, and the adapters map the extraction vocabulary correctly;
  * integration through the REAL ComplianceEngine: ExtractedDeclaration -> adapter ->
    engine produces the expected legal status, proving the contracts drive the
    unchanged core and that malformed/uncertain input never becomes COMPLIANT.

No OCR, no database, no network.
"""

from datetime import date, datetime

import pytest
from pydantic import ValidationError

from app.core.enums import (
    ComplianceStatus,
    DeclarationSource,
    DeclarationStatus,
    DetectionStatus,
    ObservationSource,
    VerificationOutcome,
    VerificationStatus,
)
from app.schemas.assessment import ComplianceAssessment
from app.schemas.contracts import (
    CONFIRMED_ABSENT_CONFIDENCE,
    EvidenceReference,
    ExtractedDeclaration,
    InspectionContext,
    MeasuredValue,
    NutritionFacts,
    NutritionValue,
    ProductProfile,
    ScanResult,
    VerificationInput,
    VerificationResult,
    detection_to_declaration_status,
)
from app.schemas.contracts.verification import MeasuredValue as _MV  # noqa: F401  (import-path check)
from app.schemas.declaration import Declaration
from app.schemas.ingredient import IngredientItem
from tests.fixtures.inspections import engine
from tests.fixtures.rules import fixture_rule


def _mrp_required_rule():
    """A REQUIRED_DECLARATION rule that requires the 'mrp' field. Not official text."""
    return fixture_rule(
        rule_code="TEST-C11-MRP",
        applicability_condition={"applies_to_categories": ["*"], "declaration_fields": ["mrp"]},
    )


def _context(**overrides) -> InspectionContext:
    payload = dict(
        inspection_datetime=date(2026, 8, 23),
        product_category="HOUSEHOLD_PRODUCT",
        label_readable=True,
    )
    payload.update(overrides)
    return InspectionContext(**payload)


# ---------------------------------------------------------------------------
# ExtractedDeclaration: shape + validation
# ---------------------------------------------------------------------------


def test_extracted_declaration_accepts_valid_detected() -> None:
    d = ExtractedDeclaration.model_validate(
        {"field": "mrp", "value": "50", "unit": "INR", "confidence": 0.98, "status": "DETECTED"}
    )
    assert d.status is DetectionStatus.DETECTED
    assert d.source is DeclarationSource.OCR  # default


def test_extracted_declaration_rejects_unknown_status() -> None:
    with pytest.raises(ValidationError):
        ExtractedDeclaration.model_validate({"field": "mrp", "status": "MISSING"})


def test_extracted_declaration_rejects_out_of_range_confidence() -> None:
    with pytest.raises(ValidationError):
        ExtractedDeclaration.model_validate({"field": "mrp", "status": "DETECTED", "confidence": 1.5})


def test_extracted_declaration_rejects_unknown_field_extra_forbid() -> None:
    with pytest.raises(ValidationError):
        ExtractedDeclaration.model_validate({"field": "mrp", "status": "DETECTED", "bogus": 1})


def test_extracted_declaration_bbox_wrong_length_rejected() -> None:
    with pytest.raises(ValidationError):
        ExtractedDeclaration.model_validate({"field": "mrp", "status": "DETECTED", "bbox": [1, 2, 3]})


def test_extracted_declaration_bbox_unordered_rejected() -> None:
    with pytest.raises(ValidationError):
        ExtractedDeclaration.model_validate(
            {"field": "mrp", "status": "DETECTED", "bbox": [30, 40, 10, 20]}
        )


# ---------------------------------------------------------------------------
# Adapter: DetectionStatus -> DeclarationStatus
# ---------------------------------------------------------------------------


def test_detection_status_is_distinct_from_declaration_status() -> None:
    # Richer extraction vocabulary; the two enums are not the same type.
    assert DetectionStatus is not DeclarationStatus
    assert {s.value for s in DetectionStatus} >= {"CONFIRMED_ABSENT", "UNCERTAIN", "NOT_APPLICABLE"}


def test_status_mapping_covers_every_detection_status() -> None:
    mapping = {s: detection_to_declaration_status(s) for s in DetectionStatus}
    assert mapping == {
        DetectionStatus.DETECTED: DeclarationStatus.DETECTED,
        DetectionStatus.UNCERTAIN: DeclarationStatus.LOW_CONFIDENCE,
        DetectionStatus.NOT_DETECTED: DeclarationStatus.NOT_DETECTED,
        DetectionStatus.CONFIRMED_ABSENT: DeclarationStatus.NOT_DETECTED,
        DetectionStatus.NOT_APPLICABLE: None,
    }


def test_to_declaration_not_applicable_is_dropped() -> None:
    d = ExtractedDeclaration(field="origin", status=DetectionStatus.NOT_APPLICABLE)
    assert d.to_declaration() is None


def test_to_declaration_confirmed_absent_gets_high_confidence_not_detected() -> None:
    d = ExtractedDeclaration(field="mrp", status=DetectionStatus.CONFIRMED_ABSENT)
    legal = d.to_declaration(label_readable=True)
    assert legal is not None
    assert legal.status is DeclarationStatus.NOT_DETECTED
    assert legal.confidence is not None and legal.confidence >= CONFIRMED_ABSENT_CONFIDENCE


def test_to_declaration_uncertain_becomes_low_confidence() -> None:
    d = ExtractedDeclaration(field="mrp", status=DetectionStatus.UNCERTAIN, confidence=0.5)
    legal = d.to_declaration()
    assert legal is not None and legal.status is DeclarationStatus.LOW_CONFIDENCE


def test_to_declaration_detected_passes_value_through() -> None:
    d = ExtractedDeclaration(field="mrp", value="50", status=DetectionStatus.DETECTED, confidence=0.98)
    legal = d.to_declaration()
    assert legal is not None and legal.value == "50" and legal.status is DeclarationStatus.DETECTED


# ---------------------------------------------------------------------------
# InspectionContext adapters
# ---------------------------------------------------------------------------


def test_context_builds_product_context() -> None:
    ctx = _context(is_imported=True, size_is_relevant=True)
    pc = ctx.to_product_context()
    assert pc.category == "HOUSEHOLD_PRODUCT"
    assert pc.is_imported is True
    assert pc.inspection_date == date(2026, 8, 23)


def test_context_request_adapts_and_drops_not_applicable() -> None:
    ctx = _context()
    req = ctx.to_compliance_request(
        [
            ExtractedDeclaration(field="origin", status=DetectionStatus.NOT_APPLICABLE),
            ExtractedDeclaration(field="mrp", value="50", status=DetectionStatus.DETECTED, confidence=0.98),
        ]
    )
    fields = [d.field for d in req.declarations]
    assert "origin" not in fields  # NOT_APPLICABLE dropped
    assert "mrp" in fields
    assert req.label_readable is True


def test_context_request_passes_legal_declaration_through() -> None:
    ctx = _context()
    legal = Declaration.model_validate(
        {"field": "mrp", "value": "50", "status": "DETECTED", "confidence": 0.98}
    )
    req = ctx.to_compliance_request([legal])
    assert req.declarations[0].field == "mrp"


def test_context_accepts_datetime_for_historical_selection() -> None:
    ctx = _context(inspection_datetime=datetime(2024, 6, 1, 10, 0, 0))
    assert ctx.to_product_context().inspection_date == datetime(2024, 6, 1, 10, 0, 0)


# ---------------------------------------------------------------------------
# Integration through the REAL engine
# ---------------------------------------------------------------------------


def test_confirmed_absent_readable_is_potential_non_compliance() -> None:
    ctx = _context(label_readable=True)
    req = ctx.to_compliance_request([ExtractedDeclaration(field="mrp", status=DetectionStatus.CONFIRMED_ABSENT)])
    result = engine([_mrp_required_rule()]).evaluate(req)

    assert result.status is ComplianceStatus.POTENTIAL_NON_COMPLIANCE
    assert result.violation_count == 1


def test_uncertain_is_manual_review_never_compliant() -> None:
    ctx = _context(label_readable=True)
    req = ctx.to_compliance_request(
        [ExtractedDeclaration(field="mrp", status=DetectionStatus.UNCERTAIN, confidence=0.5)]
    )
    result = engine([_mrp_required_rule()]).evaluate(req)

    assert result.status is ComplianceStatus.MANUAL_REVIEW
    assert result.status is not ComplianceStatus.COMPLIANT
    assert result.violation_count == 0


def test_confirmed_absent_without_readable_label_falls_back_to_manual_review() -> None:
    # label_readable unknown => the engine cannot trust the absence => MANUAL_REVIEW,
    # never a silent COMPLIANT.
    ctx = _context(label_readable=None)
    req = ctx.to_compliance_request([ExtractedDeclaration(field="mrp", status=DetectionStatus.CONFIRMED_ABSENT)])
    result = engine([_mrp_required_rule()]).evaluate(req)

    assert result.status is ComplianceStatus.MANUAL_REVIEW
    assert result.status is not ComplianceStatus.COMPLIANT


def test_detected_value_passes_through_to_compliant() -> None:
    ctx = _context(label_readable=True)
    req = ctx.to_compliance_request(
        [ExtractedDeclaration(field="mrp", value="50", status=DetectionStatus.DETECTED, confidence=0.98)]
    )
    result = engine([_mrp_required_rule()]).evaluate(req)

    assert result.status is ComplianceStatus.COMPLIANT
    assert result.passed_count == 1


def test_detected_but_empty_value_is_manual_review_not_compliant() -> None:
    # Malformed: a value was claimed present but is blank. Must not become COMPLIANT.
    ctx = _context(label_readable=True)
    req = ctx.to_compliance_request(
        [ExtractedDeclaration(field="mrp", value="", status=DetectionStatus.DETECTED, confidence=0.98)]
    )
    result = engine([_mrp_required_rule()]).evaluate(req)

    assert result.status is ComplianceStatus.MANUAL_REVIEW
    assert result.status is not ComplianceStatus.COMPLIANT


# ---------------------------------------------------------------------------
# Verification contracts (shape only; no algorithm, no fraud verdicts)
# ---------------------------------------------------------------------------


def test_verification_outcome_has_no_fraud_or_illegal_members() -> None:
    values = {v.value for v in VerificationOutcome}
    assert values == {"MATCH", "POTENTIAL_MISMATCH", "COULD_NOT_VERIFY", "MANUAL_REVIEW", "NOT_APPLICABLE"}
    assert not (values & {"FRAUD", "CHEATING", "ILLEGAL"})


def test_verification_outcome_is_not_verification_status() -> None:
    # Deliberately a different enum than the legal rule-row VerificationStatus.
    assert VerificationOutcome is not VerificationStatus


def test_verification_input_allows_missing_observation() -> None:
    vi = VerificationInput(field="net_quantity", expected=MeasuredValue(value=500, unit="g"))
    assert vi.observed is None  # no observation yet


def test_verification_result_could_not_verify_with_no_observation() -> None:
    vr = VerificationResult(
        field="net_quantity",
        expected=MeasuredValue(value=500, unit="g"),
        observed=None,
        status=VerificationOutcome.COULD_NOT_VERIFY,
    )
    assert vr.observed is None
    assert vr.status is VerificationOutcome.COULD_NOT_VERIFY


def test_verification_result_records_observation_source() -> None:
    vr = VerificationResult(
        field="net_quantity",
        expected=MeasuredValue(value=500, unit="g"),
        observed=MeasuredValue(value=472, unit="g"),
        status=VerificationOutcome.POTENTIAL_MISMATCH,
        observation_source=ObservationSource.USER_PROVIDED,
        difference=-28,
    )
    assert vr.observation_source is ObservationSource.USER_PROVIDED


# ---------------------------------------------------------------------------
# Nutrition contracts: missing is null, never zero
# ---------------------------------------------------------------------------


def test_nutrition_value_defaults_to_unknown_not_zero() -> None:
    nv = NutritionValue()
    assert nv.amount is None
    assert nv.is_known is False


def test_nutrition_value_real_zero_is_known() -> None:
    nv = NutritionValue(amount=0.0, unit="g", status=DetectionStatus.DETECTED)
    assert nv.is_known is True  # a declared 0 g is a real value


def test_nutrition_facts_empty_has_no_implied_zeros() -> None:
    facts = NutritionFacts()
    for field in ("energy", "protein", "carbohydrates", "total_sugar", "added_sugar",
                  "fat", "saturated_fat", "trans_fat", "fiber", "sodium"):
        assert getattr(facts, field) is None  # unknown, not 0


# ---------------------------------------------------------------------------
# Evidence, product, ingredient, scan aggregate
# ---------------------------------------------------------------------------


def test_evidence_reference_validates_bbox_order() -> None:
    with pytest.raises(ValidationError):
        EvidenceReference.model_validate(
            {"evidence_id": "e1", "evidence_type": "OCR_REGION", "bbox": [30, 40, 10, 20]}
        )


def test_product_profile_is_fully_optional_and_has_no_db_id() -> None:
    p = ProductProfile()
    assert p.name is None and p.mrp is None
    assert "id" not in ProductProfile.model_fields  # pre-persistence: no UUID


def test_ingredient_item_backward_compatible() -> None:
    # Original two-field payload still validates unchanged.
    old = IngredientItem.model_validate({"name": "Sugar", "raw_text": "SUGAR"})
    assert old.normalized_name is None and old.position is None
    # New optional fields accepted.
    new = IngredientItem.model_validate(
        {"name": "Sugar", "normalized_name": "sugar", "position": 0, "confidence": 0.9}
    )
    assert new.position == 0


def test_scan_result_defaults_are_safe() -> None:
    sr = ScanResult(scan_id="scan_1")
    assert sr.legal_assessment is None  # engine not run != COMPLIANT
    assert sr.declarations == [] and sr.verification == [] and sr.ingredients == []
    assert sr.nutrition is None
    assert sr.warnings == []


def test_scan_result_reuses_engine_assessment_type() -> None:
    ctx = _context(label_readable=True)
    req = ctx.to_compliance_request(
        [ExtractedDeclaration(field="mrp", value="50", status=DetectionStatus.DETECTED, confidence=0.98)]
    )
    assessment = engine([_mrp_required_rule()]).evaluate(req)
    sr = ScanResult(scan_id="scan_1", legal_assessment=assessment)

    assert isinstance(sr.legal_assessment, ComplianceAssessment)  # reused, not duplicated
    assert sr.legal_assessment.status is ComplianceStatus.COMPLIANT
