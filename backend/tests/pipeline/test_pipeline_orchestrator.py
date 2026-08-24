"""Phase 19: scan orchestration into the unified ScanResult.

Asserts the orchestrator coordinates the earlier phases without becoming a new engine,
and honours the milestone's boundaries:
  * a stage that lacks its input is SKIPPED, a stage that errors is FAILED -- the scan
    still returns a ScanResult (partial results, never a crash);
  * a skipped/failed legal stage leaves legal_assessment=None (never implied COMPLIANT);
  * legal runs regardless of nutrition, and missing nutrition stays None (not zero);
  * verification and guidance flow through, carrying their caveats intact.
"""

from datetime import date

from app.core.enums import (
    ComplianceStatus,
    DetectionStatus,
    ProductCategory,
    RuleStatus,
    StageOutcome,
    VerificationOutcome,
    VerificationStatus,
)
from app.pipeline import run_scan
from app.schemas.contracts.context import InspectionContext
from app.schemas.contracts.nutrition import NutritionFacts, NutritionValue
from app.schemas.contracts.scan import ScanResult
from app.schemas.contracts.verification import MeasuredValue, VerificationInput
from app.schemas.legal_rule import LegalRuleRecord
from app.schemas.ocr import OCRResult
from tests.fixtures.inspections import engine as make_engine

INSPECTION_DATE = date(2026, 8, 23)


def _ocr(text, confidence=0.95, bbox=(0, 0, 120, 20)):
    return OCRResult(text=text, confidence=confidence, bbox=list(bbox))


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


def _rules():
    return [_rule("LM-PC-MRP-001", "MRP_VALIDATION", ["mrp"]), _rule("LM-PC-NETQ-001", "NET_QUANTITY_VALIDATION", ["net_quantity"])]


def _context(**kw):
    return InspectionContext(inspection_datetime=INSPECTION_DATE, product_category=ProductCategory.PACKAGED_FOOD, **kw)


def _stage_map(scan: ScanResult) -> dict[str, StageOutcome]:
    return {s.stage: s.status for s in scan.stages}


class _BoomEngine:
    """A stand-in engine that fails, to prove a stage error is surfaced, not fatal."""

    def evaluate(self, _request):
        raise RuntimeError("simulated engine failure")


# --------------------------------------------------------------------------- #
# happy path
# --------------------------------------------------------------------------- #


def test_full_scan_assembles_unified_result():
    scan = run_scan(
        scan_id="scan_1",
        ocr_results=[_ocr("MRP ₹50"), _ocr("Net Quantity 500 g")],
        engine=make_engine(_rules()),
        context=_context(),
    )
    assert isinstance(scan, ScanResult)
    assert scan.scan_id == "scan_1"
    assert scan.legal_assessment is not None
    assert scan.legal_assessment.status is ComplianceStatus.COMPLIANT
    assert len(scan.declarations) == 2
    assert scan.guidance is not None
    stages = _stage_map(scan)
    assert stages["extraction"] is StageOutcome.COMPLETED
    assert stages["legal"] is StageOutcome.COMPLETED
    assert stages["guidance"] is StageOutcome.COMPLETED
    assert stages["verification"] is StageOutcome.SKIPPED  # no observed values supplied
    assert stages["nutrition"] is StageOutcome.SKIPPED


# --------------------------------------------------------------------------- #
# legal independence from nutrition; missing != zero
# --------------------------------------------------------------------------- #


def test_legal_runs_even_when_nutrition_missing():
    scan = run_scan(
        scan_id="scan_2",
        ocr_results=[_ocr("MRP ₹50"), _ocr("Net Quantity 500 g")],
        engine=make_engine(_rules()),
        context=_context(),
        nutrition=None,
    )
    assert scan.legal_assessment is not None
    assert scan.legal_assessment.status is ComplianceStatus.COMPLIANT
    assert scan.nutrition is None  # missing, not zero
    assert _stage_map(scan)["nutrition"] is StageOutcome.SKIPPED
    assert any("not zero" in (s.detail or "") for s in scan.stages if s.stage == "nutrition")


def test_nutrition_is_carried_through_unchanged_without_comparison():
    facts = NutritionFacts(energy=NutritionValue(amount=250, unit="kcal", status=DetectionStatus.DETECTED))
    scan = run_scan(
        scan_id="scan_3",
        ocr_results=[_ocr("MRP ₹50")],
        engine=make_engine(_rules()),
        context=_context(),
        nutrition=facts,
    )
    assert scan.nutrition is facts  # carried, not re-derived or compared
    assert _stage_map(scan)["nutrition"] is StageOutcome.COMPLETED


# --------------------------------------------------------------------------- #
# partial results: missing inputs SKIP, errors FAIL, never crash
# --------------------------------------------------------------------------- #


def test_missing_engine_skips_legal_without_implying_compliant():
    scan = run_scan(scan_id="scan_4", ocr_results=[_ocr("MRP ₹50")], engine=None, context=_context())
    assert scan.legal_assessment is None  # engine not run != COMPLIANT
    assert scan.guidance is None
    assert len(scan.declarations) == 1  # extraction still ran
    stages = _stage_map(scan)
    assert stages["extraction"] is StageOutcome.COMPLETED
    assert stages["legal"] is StageOutcome.SKIPPED
    assert stages["guidance"] is StageOutcome.SKIPPED


def test_empty_scan_returns_result_without_crashing():
    scan = run_scan(scan_id="scan_5")
    assert isinstance(scan, ScanResult)
    assert scan.declarations == []
    assert scan.legal_assessment is None
    stages = _stage_map(scan)
    assert stages["extraction"] is StageOutcome.COMPLETED  # zero fields is a valid extraction
    assert stages["legal"] is StageOutcome.SKIPPED
    assert stages["verification"] is StageOutcome.SKIPPED
    assert stages["guidance"] is StageOutcome.SKIPPED
    assert stages["nutrition"] is StageOutcome.SKIPPED


def test_engine_failure_is_surfaced_not_fatal():
    scan = run_scan(
        scan_id="scan_6",
        ocr_results=[_ocr("MRP ₹50")],
        engine=_BoomEngine(),
        context=_context(),
    )
    # The scan did not raise; the failure is recorded and downstream degrades gracefully.
    assert scan.legal_assessment is None
    stages = _stage_map(scan)
    assert stages["extraction"] is StageOutcome.COMPLETED
    assert stages["legal"] is StageOutcome.FAILED
    assert any("RuntimeError" in (s.detail or "") for s in scan.stages if s.stage == "legal")
    assert stages["guidance"] is StageOutcome.SKIPPED
    assert any("Legal assessment failed" in w for w in scan.warnings)


# --------------------------------------------------------------------------- #
# verification + guidance flow through with caveats intact
# --------------------------------------------------------------------------- #


def test_verification_flows_into_result_and_guidance_carries_caveat():
    vi = VerificationInput(
        field="net_quantity",
        expected=MeasuredValue(value=500, unit="g"),
        observed=MeasuredValue(value=450, unit="g"),
        observation_confidence=0.9,
    )
    scan = run_scan(
        scan_id="scan_7",
        ocr_results=[_ocr("Net Quantity 500 g")],
        engine=make_engine(_rules()),
        context=_context(),
        verification_inputs=[vi],
    )
    assert len(scan.verification) == 1
    assert scan.verification[0].status is VerificationOutcome.POTENTIAL_MISMATCH
    assert _stage_map(scan)["verification"] is StageOutcome.COMPLETED
    assert scan.guidance is not None
    assert any("cannot measure the actual physical weight or volume" in lim for lim in scan.guidance.limitations)


def test_scan_is_deterministic():
    kwargs = dict(
        scan_id="scan_8",
        ocr_results=[_ocr("MRP ₹50"), _ocr("Net Quantity 500 g")],
        engine=make_engine(_rules()),
        context=_context(),
    )
    first = run_scan(**kwargs).model_dump()
    # a fresh engine instance, same rules -> identical result
    kwargs["engine"] = make_engine(_rules())
    second = run_scan(**kwargs).model_dump()
    assert first == second
