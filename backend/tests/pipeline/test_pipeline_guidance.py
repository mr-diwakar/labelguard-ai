"""Phase 18: consumer guidance (assessment + verification -> plain-language help).

These tests assert the guidance layer explains verdicts without changing them, and
honours every boundary of the spec:
  * a POTENTIAL_NON_COMPLIANCE is reported as something to check, never as fraud;
  * a MANUAL_REVIEW / COULD_NOT_VERIFY is reported as uncertainty, never as a problem;
  * the physical-quantity caveat and every verification note are carried, not dropped;
  * evidence-to-keep reuses EvidenceReference;
  * LabelGuard never claims to have filed a complaint or contacted an authority.
"""

from datetime import date

from app.core.enums import (
    ComplianceStatus,
    EvidenceType,
    FindingKind,
    ProductCategory,
    RuleStatus,
    Severity,
    ValidationOutcome,
    VerificationOutcome,
    VerificationStatus,
)
from app.extraction import extract_declarations
from app.pipeline import assess_extraction, build_guidance, verify_one
from app.schemas.assessment import AssessmentItem, ComplianceAssessment
from app.schemas.contracts.evidence import EvidenceReference
from app.schemas.contracts.guidance import ConsumerGuidance, GuidanceItem
from app.schemas.contracts.verification import MeasuredValue, VerificationInput
from app.schemas.legal_rule import LegalRuleRecord
from app.schemas.ocr import OCRResult
from app.schemas.validation import ValidationEvidence
from tests.fixtures.inspections import engine as make_engine

_FORBIDDEN_WORDS = ("fraud", "counterfeit", "illegal", "cheating", "criminal", "fake")

# Phrases that would falsely claim LabelGuard took an action on the consumer's behalf.
_FALSE_ACTION_CLAIMS = (
    "we filed",
    "we have filed",
    "complaint has been filed",
    "complaint was filed",
    "we reported",
    "we have reported",
    "we submitted",
    "submitted to the",
    "filed on your behalf",
    "reported to the authority",
    "reported to the legal metrology",
)


# --------------------------------------------------------------------------- #
# builders
# --------------------------------------------------------------------------- #


def _item(
    rule_code,
    result,
    *,
    severity=Severity.UNSPECIFIED,
    reason="reason text",
    recommended_action=None,
    evidence=None,
    rule_name=None,
):
    return AssessmentItem(
        rule_id=rule_code,
        rule_code=rule_code,
        rule_name=rule_name or rule_code,
        result=result,
        reason=reason,
        recommended_action=recommended_action,
        severity=severity,
        evidence=evidence or [],
    )


def _assessment(status, *, violations=(), manual_review=(), passed=(), warnings=()):
    return ComplianceAssessment(
        status=status,
        passed=list(passed),
        violations=list(violations),
        manual_review=list(manual_review),
        not_applicable=[],
        warnings=list(warnings),
        rule_count=len(passed) + len(violations) + len(manual_review),
        passed_count=len(passed),
        violation_count=len(violations),
        manual_review_count=len(manual_review),
        not_applicable_count=0,
        explanation="Automated assessment. This is not a legal determination.",
        results=[],
    )


def _all_strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for value in obj.values():
            yield from _all_strings(value)
    elif isinstance(obj, (list, tuple)):
        for value in obj:
            yield from _all_strings(value)


def _text(guidance: ConsumerGuidance) -> str:
    return " ".join(_all_strings(guidance.model_dump())).lower()


# --------------------------------------------------------------------------- #
# all-clear case
# --------------------------------------------------------------------------- #


def test_compliant_scan_produces_all_clear_guidance():
    guidance = build_guidance(_assessment(ComplianceStatus.COMPLIANT, passed=[_item("R1", ValidationOutcome.PASS)]))
    assert isinstance(guidance, ConsumerGuidance)
    assert guidance.status is ComplianceStatus.COMPLIANT
    assert guidance.items == []
    assert any("no labelling issue" in line.lower() for line in guidance.what_we_found)
    # Even with nothing wrong, the consumer is still told what to keep and the disclaimer.
    assert guidance.what_evidence_to_keep
    assert guidance.disclaimer
    assert guidance.what_you_can_do_next


# --------------------------------------------------------------------------- #
# a violation is a thing to check, never fraud
# --------------------------------------------------------------------------- #


def test_violation_becomes_potential_non_compliance_item():
    assessment = _assessment(
        ComplianceStatus.POTENTIAL_NON_COMPLIANCE,
        violations=[
            _item(
                "LM-PC-NETQ-001",
                ValidationOutcome.POTENTIAL_NON_COMPLIANCE,
                severity=Severity.HIGH,
                rule_name="Net quantity declaration",
                recommended_action="Check the net quantity printed on the pack.",
            )
        ],
    )
    guidance = build_guidance(assessment)
    assert len(guidance.items) == 1
    item = guidance.items[0]
    assert item.finding_kind is FindingKind.POTENTIAL_NON_COMPLIANCE
    assert item.severity is Severity.HIGH
    assert item.source_reference == "LM-PC-NETQ-001"
    # the consumer is told it is not proven, and that the authority alone decides
    assert any("not a proven violation" in lim.lower() for lim in item.limitations)
    assert "legal metrology" in _text(guidance)
    # the engine's recommended action flows through to the consumer's next steps
    assert "Check the net quantity printed on the pack." in item.next_steps
    assert "Check the net quantity printed on the pack." in guidance.what_you_can_do_next


def test_manual_review_is_reported_as_uncertain_not_problem():
    assessment = _assessment(
        ComplianceStatus.MANUAL_REVIEW,
        manual_review=[_item("LM-PC-MRP-001", ValidationOutcome.MANUAL_REVIEW, rule_name="MRP declaration")],
    )
    guidance = build_guidance(assessment)
    assert guidance.status is ComplianceStatus.MANUAL_REVIEW
    assert len(guidance.items) == 1
    assert guidance.items[0].finding_kind is FindingKind.MANUAL_REVIEW
    # it appears under "what is uncertain", and NOT framed as a found problem
    assert guidance.what_is_uncertain
    assert any("could not automatically confirm" in it.issue.lower() for it in guidance.items)


# --------------------------------------------------------------------------- #
# never accuses; never claims to have acted
# --------------------------------------------------------------------------- #


def test_no_fraud_language_anywhere():
    assessment = _assessment(
        ComplianceStatus.POTENTIAL_NON_COMPLIANCE,
        violations=[_item("R1", ValidationOutcome.POTENTIAL_NON_COMPLIANCE, severity=Severity.CRITICAL)],
        manual_review=[_item("R2", ValidationOutcome.MANUAL_REVIEW)],
    )
    text = _text(build_guidance(assessment))
    assert not any(word in text for word in _FORBIDDEN_WORDS)


def test_never_claims_labelguard_filed_or_reported_anything():
    assessment = _assessment(
        ComplianceStatus.POTENTIAL_NON_COMPLIANCE,
        violations=[_item("R1", ValidationOutcome.POTENTIAL_NON_COMPLIANCE)],
    )
    guidance = build_guidance(assessment)
    text = _text(guidance)
    assert not any(claim in text for claim in _FALSE_ACTION_CLAIMS)
    # and it says so explicitly, in the disclaimer
    assert "filed no complaint" in text or "not filed any complaint" in text
    assert "not contacted any seller or authority" in guidance.disclaimer.lower()


# --------------------------------------------------------------------------- #
# verification -> guidance
# --------------------------------------------------------------------------- #


def test_physical_quantity_caveat_is_carried_from_verification():
    result = verify_one(
        VerificationInput(
            field="net_quantity",
            expected=MeasuredValue(value=500, unit="g"),
            observed=MeasuredValue(value=450, unit="g"),
            observation_confidence=0.9,
        )
    )
    assert result.status is VerificationOutcome.POTENTIAL_MISMATCH
    guidance = build_guidance(_assessment(ComplianceStatus.MANUAL_REVIEW), verification=[result])
    text = _text(guidance)
    assert "cannot measure the actual physical weight or volume" in text
    assert "not a determination of wrongdoing" in text


def test_matching_verification_is_not_surfaced_as_an_issue():
    result = verify_one(
        VerificationInput(
            field="mrp",
            expected=MeasuredValue(value=50, unit="INR"),
            observed=MeasuredValue(value=50, unit="INR"),
            observation_confidence=0.9,
        )
    )
    assert result.status is VerificationOutcome.MATCH
    guidance = build_guidance(_assessment(ComplianceStatus.COMPLIANT), verification=[result])
    assert all(it.source_reference != "mrp" for it in guidance.items)
    assert guidance.items == []


# --------------------------------------------------------------------------- #
# evidence-to-keep reuses EvidenceReference
# --------------------------------------------------------------------------- #


def test_evidence_to_keep_reuses_evidence_reference_and_is_deduped():
    ev = ValidationEvidence(field="net_quantity", value="500 g", source="paddleocr", bbox=[10, 20, 90, 40], confidence=0.9)
    assessment = _assessment(
        ComplianceStatus.POTENTIAL_NON_COMPLIANCE,
        violations=[_item("R1", ValidationOutcome.POTENTIAL_NON_COMPLIANCE, evidence=[ev])],
    )
    already = EvidenceReference(evidence_id="keep_product_photo", evidence_type=EvidenceType.PRODUCT_IMAGE)
    guidance = build_guidance(assessment, evidence=[already])
    keep = guidance.what_evidence_to_keep
    assert keep and all(isinstance(ref, EvidenceReference) for ref in keep)
    ids = [ref.evidence_id for ref in keep]
    assert len(ids) == len(set(ids))  # deduped by evidence_id
    assert "keep_product_photo" in ids  # baseline present, not duplicated by the passed-in one


# --------------------------------------------------------------------------- #
# end-to-end + determinism
# --------------------------------------------------------------------------- #


def _rule(rule_code, validation_type, fields):
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
            "applicability_condition": {"applies_to_categories": ["*"], "declaration_fields": fields},
        }
    )


def test_end_to_end_missing_field_surfaces_one_problem():
    # MRP read, net quantity absent, label asserted readable -> engine finds one violation.
    extraction = extract_declarations([OCRResult(text="MRP ₹50", confidence=0.95, bbox=[0, 0, 120, 20])])
    engine = make_engine([_rule("LM-PC-MRP-001", "MRP_VALIDATION", ["mrp"]), _rule("LM-PC-NETQ-001", "NET_QUANTITY_VALIDATION", ["net_quantity"])])
    assessment = assess_extraction(
        engine,
        extraction,
        inspection_date=date(2026, 8, 23),
        product_category=ProductCategory.PACKAGED_FOOD,
        label_readable=True,
    )
    assert assessment.status is ComplianceStatus.POTENTIAL_NON_COMPLIANCE
    guidance = build_guidance(assessment)
    problems = [it for it in guidance.items if it.finding_kind is FindingKind.POTENTIAL_NON_COMPLIANCE]
    assert len(problems) == 1
    assert problems[0].source_reference == "LM-PC-NETQ-001"


def test_guidance_is_deterministic():
    assessment = _assessment(
        ComplianceStatus.POTENTIAL_NON_COMPLIANCE,
        violations=[_item("R1", ValidationOutcome.POTENTIAL_NON_COMPLIANCE)],
        manual_review=[_item("R2", ValidationOutcome.MANUAL_REVIEW)],
    )
    first = build_guidance(assessment).model_dump()
    second = build_guidance(assessment).model_dump()
    assert first == second
