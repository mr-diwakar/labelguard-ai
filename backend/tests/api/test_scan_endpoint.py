"""API wiring for the unified scan endpoint (Phase 19 -> HTTP).

Exercises the route handler directly and asserts route registration, matching the
project's existing endpoint tests (Starlette's ``TestClient`` path is deprecated/unavailable
in this environment, so no HTTP client is used). The engine dependency is overridden with
the in-memory ``StaticRuleResolver`` fixture, so these tests need no database -- exactly how
the orchestrator tests build their engine.

The point of this suite is to prove the endpoint delegates to ``run_scan`` *faithfully*:
  * it builds a real ``ComplianceEngine`` so the legal + guidance stages actually run
    (the originally-committed handler passed no engine, so both were always SKIPPED);
  * it forwards every optional input (nutrition/product/ingredients/evidence), which the
    original handler silently dropped;
  * it generates a scan_id, and never crashes on partial input.
"""

from datetime import date

import pytest
from pydantic import ValidationError

from app.api.scan import create_scan, get_compliance_engine, router
from app.compliance.engine import ComplianceEngine
from app.compliance.rule_loader import RuleLoader
from app.core.enums import (
    ComplianceStatus,
    DetectionStatus,
    ProductCategory,
    RuleStatus,
    StageOutcome,
    VerificationOutcome,
    VerificationStatus,
)
from app.schemas.contracts.context import InspectionContext
from app.schemas.contracts.nutrition import NutritionFacts, NutritionValue
from app.schemas.contracts.scan import ScanRequest, ScanResult
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
    return [
        _rule("LM-PC-MRP-001", "MRP_VALIDATION", ["mrp"]),
        _rule("LM-PC-NETQ-001", "NET_QUANTITY_VALIDATION", ["net_quantity"]),
    ]


def _context(**kw):
    return InspectionContext(inspection_datetime=INSPECTION_DATE, product_category=ProductCategory.PACKAGED_FOOD, **kw)


def _stage_map(scan: ScanResult) -> dict[str, StageOutcome]:
    return {s.stage: s.status for s in scan.stages}


# --------------------------------------------------------------------------- #
# route registration
# --------------------------------------------------------------------------- #


def test_scan_route_is_registered_as_post():
    registered = {(tuple(sorted(r.methods)), r.path) for r in router.routes}
    assert (("POST",), "/scan") in registered


# --------------------------------------------------------------------------- #
# the fix: a real engine is built, so legal + guidance actually run
# --------------------------------------------------------------------------- #


def test_handler_runs_full_scan_including_legal_and_guidance():
    request = ScanRequest(
        scan_id="scan_api_full",
        ocr_results=[_ocr("MRP ₹50"), _ocr("Net Quantity 500 g")],
        context=_context(),
    )
    result = create_scan(request, engine=make_engine(_rules()))

    assert isinstance(result, ScanResult)
    assert result.scan_id == "scan_api_full"
    # These were ALWAYS None with the original engine-less handler.
    assert result.legal_assessment is not None
    assert result.legal_assessment.status is ComplianceStatus.COMPLIANT
    assert result.guidance is not None
    assert len(result.declarations) == 2
    stages = _stage_map(result)
    assert stages["extraction"] is StageOutcome.COMPLETED
    assert stages["legal"] is StageOutcome.COMPLETED
    assert stages["guidance"] is StageOutcome.COMPLETED


def test_handler_forwards_optional_inputs_the_minimal_version_dropped():
    # The originally-committed endpoint forwarded only ocr_results/context/verification_inputs.
    # Assert nutrition (carried) AND verification (run) both reach run_scan through the route.
    facts = NutritionFacts(energy=NutritionValue(amount=250, unit="kcal", status=DetectionStatus.DETECTED))
    vi = VerificationInput(
        field="net_quantity",
        expected=MeasuredValue(value=500, unit="g"),
        observed=MeasuredValue(value=450, unit="g"),
        observation_confidence=0.9,
    )
    request = ScanRequest(
        ocr_results=[_ocr("Net Quantity 500 g")],
        context=_context(),
        nutrition=facts,
        verification_inputs=[vi],
    )
    result = create_scan(request, engine=make_engine(_rules()))

    assert result.nutrition is facts  # carried through unchanged, not dropped
    assert _stage_map(result)["nutrition"] is StageOutcome.COMPLETED
    assert len(result.verification) == 1
    assert result.verification[0].status is VerificationOutcome.POTENTIAL_MISMATCH


# --------------------------------------------------------------------------- #
# honest partials: no context skips legal; empty request never crashes
# --------------------------------------------------------------------------- #


def test_handler_without_context_skips_legal_without_implying_compliant():
    # Engine is present, but with no context there is nothing to assess -> SKIPPED, not COMPLIANT.
    result = create_scan(ScanRequest(ocr_results=[_ocr("MRP ₹50")]), engine=make_engine(_rules()))

    assert result.legal_assessment is None
    assert result.guidance is None
    assert len(result.declarations) == 1  # extraction still ran
    stages = _stage_map(result)
    assert stages["extraction"] is StageOutcome.COMPLETED
    assert stages["legal"] is StageOutcome.SKIPPED


def test_empty_request_returns_scan_result_without_crashing():
    result = create_scan(ScanRequest(), engine=make_engine(_rules()))

    assert isinstance(result, ScanResult)
    assert result.declarations == []
    assert result.legal_assessment is None
    assert _stage_map(result)["extraction"] is StageOutcome.COMPLETED


def test_handler_generates_scan_id_when_missing():
    result = create_scan(ScanRequest(ocr_results=[_ocr("MRP ₹50")], context=_context()), engine=make_engine(_rules()))

    assert result.scan_id
    assert len(result.scan_id) == 32  # uuid4().hex, matching app/imaging/intake.py
    int(result.scan_id, 16)  # valid hex, else ValueError


# --------------------------------------------------------------------------- #
# input contract + the engine dependency
# --------------------------------------------------------------------------- #


def test_scan_request_rejects_unknown_fields():
    # APIModel is extra="forbid": a misspelled key is a client error, not silently ignored.
    with pytest.raises(ValidationError):
        ScanRequest(bogus_field="x")


def test_get_compliance_engine_builds_db_backed_engine_without_connecting():
    sentinel = object()
    engine = get_compliance_engine(session=sentinel)

    assert isinstance(engine, ComplianceEngine)
    assert isinstance(engine.resolver, RuleLoader)
    # Built lazily: the session is held as-is; no query or connection was made.
    assert engine.resolver.repository.session is sentinel
