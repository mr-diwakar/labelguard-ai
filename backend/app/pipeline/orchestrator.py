"""
Scan orchestration (Phase 19).

Assembles one unified ``ScanResult`` from the pieces the earlier phases produce:
extraction (Phase 15) -> legal assessment (Phase 16, over the unchanged engine) ->
label-to-product verification (Phase 17) -> consumer guidance (Phase 18), with an
optional nutrition panel carried through. It is a COORDINATOR, not a new engine: every
verdict comes from the layer that owns it, and this module invents none.

Design rules, all enforced below:
  * PARTIAL RESULTS, NEVER A CRASH. Each stage runs in isolation; if one fails or lacks
    its input, it is recorded as FAILED / SKIPPED in ``ScanResult.stages`` and the scan
    continues. A caller always gets a ``ScanResult`` back.
  * FAILURES ARE SURFACED, NOT HIDDEN. A skipped legal stage leaves
    ``legal_assessment=None`` (never an implied COMPLIANT); a failed stage adds a
    warning and a structured status entry.
  * LEGAL DOES NOT DEPEND ON NUTRITION. Missing nutrition is ``None`` (never zero) and
    never blocks or changes the legal result.
  * NUTRITION COMPARISON IS NOT REBUILT HERE. A single scan carries its own
    ``NutritionFacts``; ranking multiple products remains the separate Phase 13 feature
    (``app.nutrition.comparison``), reached through its own adapter/endpoint.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.compliance.engine import ComplianceEngine
from app.core.enums import StageOutcome
from app.pipeline.guidance import build_guidance
from app.pipeline.legal import assess_extraction
from app.pipeline.verification import verify
from app.schemas.assessment import ComplianceAssessment
from app.schemas.contracts.context import InspectionContext
from app.schemas.contracts.evidence import EvidenceReference
from app.schemas.contracts.guidance import ConsumerGuidance
from app.schemas.contracts.nutrition import NutritionFacts
from app.schemas.contracts.product import ProductProfile
from app.schemas.contracts.scan import ScanResult, ScanStageStatus
from app.schemas.contracts.verification import VerificationInput, VerificationResult
from app.schemas.extraction import ExtractionResult
from app.schemas.ingredient import IngredientItem
from app.schemas.ocr import OCRResult

# Extraction lives one layer down and is imported lazily inside the stage so a broken
# extractor is caught as a stage failure rather than an import-time crash of the module.

_ERR_DETAIL_MAX = 200


def _stage(stage: str, status: StageOutcome, detail: str | None = None) -> ScanStageStatus:
    return ScanStageStatus(stage=stage, status=status, detail=detail)


def _err_detail(stage: str, exc: Exception) -> str:
    """A short, non-leaky reason for a failed stage."""
    message = str(exc).strip()
    if len(message) > _ERR_DETAIL_MAX:
        message = message[:_ERR_DETAIL_MAX] + "…"
    suffix = f": {message}" if message else ""
    return f"{stage} stage error [{type(exc).__name__}]{suffix}"


def _dedupe(lines: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for line in lines:
        if line in seen:
            continue
        seen.add(line)
        out.append(line)
    return out


def run_scan(
    *,
    scan_id: str,
    ocr_results: Sequence[OCRResult] = (),
    engine: ComplianceEngine | None = None,
    context: InspectionContext | None = None,
    verification_inputs: Sequence[VerificationInput] = (),
    nutrition: NutritionFacts | None = None,
    product: ProductProfile | None = None,
    ingredients: Sequence[IngredientItem] = (),
    evidence: Sequence[EvidenceReference] = (),
) -> ScanResult:
    """Run one scan end to end and return a unified ``ScanResult``.

    Every argument except ``scan_id`` is optional; whatever is missing simply skips the
    stage that needs it. ``engine`` + ``context`` are required for the legal stage
    (rules and inspection facts); ``verification_inputs`` for the image cross-check;
    ``nutrition`` is carried through as-is. The function never raises for a stage
    failure — inspect ``ScanResult.stages`` and ``ScanResult.warnings`` for coverage.
    """
    stages: list[ScanStageStatus] = []
    warnings: list[str] = []

    # --- Stage 1: extraction ------------------------------------------------ #
    extraction: ExtractionResult | None = None
    declarations = []
    try:
        from app.extraction import extract_declarations  # local: isolate import errors

        extraction = extract_declarations(list(ocr_results))
        declarations = extraction.to_extracted_declarations()
        warnings.extend(extraction.warnings)
        stages.append(
            _stage("extraction", StageOutcome.COMPLETED, f"{len(declarations)} field(s) extracted")
        )
    except Exception as exc:  # noqa: BLE001 - partial results by design
        stages.append(_stage("extraction", StageOutcome.FAILED, _err_detail("extraction", exc)))
        warnings.append("Declaration extraction failed; legal checks were not run on this scan.")

    # --- Stage 2: legal assessment ----------------------------------------- #
    assessment: ComplianceAssessment | None = None
    if extraction is None:
        stages.append(
            _stage("legal", StageOutcome.SKIPPED, "no declarations: extraction did not complete")
        )
    elif engine is None or context is None:
        missing = "rule engine" if engine is None else "inspection context"
        stages.append(_stage("legal", StageOutcome.SKIPPED, f"legal assessment needs a {missing}"))
    else:
        try:
            assessment = assess_extraction(
                engine,
                extraction,
                inspection_date=context.inspection_datetime,
                product_category=context.product_category,
                is_imported=context.is_imported,
                size_is_relevant=context.size_is_relevant,
                label_readable=context.label_readable,
            )
            warnings.extend(assessment.warnings)
            stages.append(
                _stage("legal", StageOutcome.COMPLETED, f"status={assessment.status.value}")
            )
        except Exception as exc:  # noqa: BLE001 - partial results by design
            stages.append(_stage("legal", StageOutcome.FAILED, _err_detail("legal", exc)))
            warnings.append("Legal assessment failed; no compliance verdict was produced for this scan.")

    # --- Stage 3: label-to-product verification ---------------------------- #
    verification: list[VerificationResult] = []
    if not verification_inputs:
        stages.append(
            _stage("verification", StageOutcome.SKIPPED, "no observed values supplied to cross-check")
        )
    else:
        try:
            verification = verify(list(verification_inputs))
            stages.append(
                _stage("verification", StageOutcome.COMPLETED, f"{len(verification)} value(s) cross-checked")
            )
        except Exception as exc:  # noqa: BLE001 - partial results by design
            stages.append(_stage("verification", StageOutcome.FAILED, _err_detail("verification", exc)))
            warnings.append("Image cross-check failed; declared values were not compared to the photo.")

    # --- Stage 4: consumer guidance ---------------------------------------- #
    guidance: ConsumerGuidance | None = None
    if assessment is None:
        stages.append(
            _stage("guidance", StageOutcome.SKIPPED, "guidance needs a completed legal assessment")
        )
    else:
        try:
            guidance = build_guidance(assessment, verification, evidence=evidence)
            stages.append(_stage("guidance", StageOutcome.COMPLETED, f"{len(guidance.items)} item(s)"))
        except Exception as exc:  # noqa: BLE001 - partial results by design
            stages.append(_stage("guidance", StageOutcome.FAILED, _err_detail("guidance", exc)))
            warnings.append("Consumer guidance could not be generated for this scan.")

    # --- Stage 5: nutrition (carried through; never blocks the legal result) #
    if nutrition is None:
        stages.append(
            _stage("nutrition", StageOutcome.SKIPPED, "no nutrition facts supplied (missing is not zero)")
        )
    else:
        stages.append(_stage("nutrition", StageOutcome.COMPLETED, "nutrition panel attached"))

    return ScanResult(
        scan_id=scan_id,
        context=context,
        product=product,
        declarations=declarations,
        legal_assessment=assessment,
        verification=verification,
        guidance=guidance,
        nutrition=nutrition,
        ingredients=list(ingredients),
        evidence=list(evidence),
        stages=stages,
        warnings=_dedupe(warnings),
    )
