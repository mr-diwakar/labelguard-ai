"""Phase 16: legal-integration adapter (extraction -> existing engine -> assessment).

These tests assert the seam behaves as an ADAPTER over the unchanged compliance
engine, and that the spec's distinctions survive the crossing:
  * a clean, complete scan -> COMPLIANT (the engine's own PASS path);
  * a field extraction simply did not detect is NOT proof of omission
    (label_readable unknown -> MANUAL_REVIEW, not POTENTIAL_NON_COMPLIANCE);
  * a genuine omission only surfaces once readability is explicitly asserted;
  * OCR letter/digit confusion and low OCR confidence -> MANUAL_REVIEW, never a
    non-compliance verdict.
"""

from datetime import date

from app.core.enums import (
    ComplianceStatus,
    DeclarationStatus,
    DetectionStatus,
    RuleStatus,
    VerificationStatus,
)
from app.extraction import extract_declarations
from app.pipeline import assess_extraction, declarations_for_engine
from app.schemas.assessment import ComplianceAssessment
from app.schemas.contracts.detection import ExtractedDeclaration
from app.schemas.legal_rule import LegalRuleRecord
from app.schemas.ocr import OCRResult
from tests.fixtures.inspections import engine as make_engine

INSPECTION_DATE = date(2026, 8, 23)


def _ocr(text: str, confidence: float = 0.95, bbox=(0, 0, 120, 20)) -> OCRResult:
    return OCRResult(text=text, confidence=confidence, bbox=list(bbox))


def _rule(rule_code: str, validation_type: str, fields: list[str]) -> LegalRuleRecord:
    return LegalRuleRecord.model_validate(
        {
            "rule_code": rule_code,
            "rule_name": "Fixture requirement",
            "description": "Not a legal requirement.",
            "requirement": "Fixture only.",
            "category": "PACKAGED_COMMODITY",
            "validation_type": validation_type,
            "source_document": "TEST",
            "source_reference": "Fixture",
            "source_version": "A",
            "effective_from": date(2011, 4, 1),
            "effective_to": None,
            "rule_status": RuleStatus.ACTIVE,
            "verification_status": VerificationStatus.VERIFIED,
            "applicability_condition": {
                "applies_to_categories": ["*"],
                "declaration_fields": fields,
            },
        }
    )


def _mrp_rule() -> LegalRuleRecord:
    return _rule("LM-PC-MRP-001", "MRP_VALIDATION", ["mrp"])


def _netq_rule() -> LegalRuleRecord:
    return _rule("LM-PC-NETQ-001", "NET_QUANTITY_VALIDATION", ["net_quantity"])


def _assess(extraction, rules, **kwargs) -> ComplianceAssessment:
    engine = make_engine(rules)
    return assess_extraction(
        engine,
        extraction,
        inspection_date=INSPECTION_DATE,
        product_category="PACKAGED_FOOD",
        **kwargs,
    )


# --------------------------------------------------------------------------- #
# Happy path: the engine, not the adapter, produces the verdict
# --------------------------------------------------------------------------- #


def test_clean_complete_scan_is_compliant():
    extraction = extract_declarations([_ocr("MRP ₹50"), _ocr("Net Quantity 500 g")])
    assessment = _assess(extraction, [_mrp_rule(), _netq_rule()])
    assert assessment.status is ComplianceStatus.COMPLIANT
    assert assessment.passed_count == 2
    assert assessment.violation_count == 0
    assert assessment.manual_review_count == 0


def test_output_is_the_existing_assessment_contract_only():
    # The adapter introduces no second verdict system: it returns the engine's own
    # ComplianceAssessment, whose status is a ComplianceStatus member.
    extraction = extract_declarations([_ocr("MRP ₹50")])
    assessment = _assess(extraction, [_mrp_rule()])
    assert isinstance(assessment, ComplianceAssessment)
    assert assessment.status in set(ComplianceStatus)
    assert "not a legal determination" in assessment.explanation


# --------------------------------------------------------------------------- #
# not detected != proof of omission (governed by label_readable)
# --------------------------------------------------------------------------- #


def test_undetected_required_field_is_manual_review_when_readability_unknown():
    # Extraction found MRP but not net quantity. With no readability determination, the
    # absent net-quantity rule must NOT become a non-compliance finding.
    extraction = extract_declarations([_ocr("MRP ₹50")])
    assessment = _assess(extraction, [_mrp_rule(), _netq_rule()])
    assert assessment.status is ComplianceStatus.MANUAL_REVIEW
    assert assessment.violation_count == 0
    assert assessment.manual_review_count == 1
    assert assessment.passed_count == 1


def test_undetected_required_field_is_potential_non_compliance_only_when_label_readable():
    # Same scan, but the caller has independently established the label was fully
    # readable -> a truly absent mandatory declaration may now surface as a finding.
    extraction = extract_declarations([_ocr("MRP ₹50")])
    assessment = _assess(extraction, [_mrp_rule(), _netq_rule()], label_readable=True)
    assert assessment.status is ComplianceStatus.POTENTIAL_NON_COMPLIANCE
    assert assessment.violation_count == 1
    assert any(item.rule_code == "LM-PC-NETQ-001" for item in assessment.violations)


# --------------------------------------------------------------------------- #
# low OCR confidence / confusion != non-compliance
# --------------------------------------------------------------------------- #


def test_ocr_letter_confusion_routes_to_manual_review_not_violation():
    # "MRP ₹5O" (letter O) is UNCERTAIN in extraction -> LOW_CONFIDENCE -> manual review.
    extraction = extract_declarations([_ocr("MRP ₹5O")])
    assessment = _assess(extraction, [_mrp_rule()], label_readable=True)
    assert assessment.status is ComplianceStatus.MANUAL_REVIEW
    assert assessment.violation_count == 0


def test_low_ocr_confidence_clean_value_is_manual_review():
    extraction = extract_declarations([_ocr("MRP ₹50", confidence=0.4)])
    assessment = _assess(extraction, [_mrp_rule()], label_readable=True)
    assert assessment.status is ComplianceStatus.MANUAL_REVIEW
    assert assessment.violation_count == 0


# --------------------------------------------------------------------------- #
# DOWN-adapter mapping
# --------------------------------------------------------------------------- #


def test_declarations_for_engine_maps_status_down_and_drops_not_applicable():
    extracted = [
        ExtractedDeclaration(field="mrp", value="50", status=DetectionStatus.DETECTED),
        ExtractedDeclaration(
            field="net_quantity", value="500 g", status=DetectionStatus.UNCERTAIN
        ),
        ExtractedDeclaration(
            field="mrp", value=None, status=DetectionStatus.NOT_APPLICABLE
        ),
    ]
    declarations = declarations_for_engine(extracted)
    by_field = {d.field: d for d in declarations}
    assert len(declarations) == 2  # NOT_APPLICABLE dropped
    assert by_field["mrp"].status is DeclarationStatus.DETECTED
    assert by_field["net_quantity"].status is DeclarationStatus.LOW_CONFIDENCE


def test_assessment_is_deterministic():
    extraction = extract_declarations([_ocr("MRP ₹50"), _ocr("Net Quantity 500 g")])
    first = _assess(extraction, [_mrp_rule(), _netq_rule()]).model_dump()
    second = _assess(extraction, [_mrp_rule(), _netq_rule()]).model_dump()
    assert first == second
