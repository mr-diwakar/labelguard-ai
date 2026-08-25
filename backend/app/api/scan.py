"""Unified scan endpoint (Phase 19 wiring) + the image-capture front door.

Two routes, ONE pipeline:

* ``POST /scan``       — starts from structured OCR JSON (``OCRResult[]``).
* ``POST /scan/image`` — starts from a captured photo, runs the existing
  ``app.imaging.process_scan`` (intake -> validation -> quality -> preprocessing ->
  OCR) and feeds ITS ``OCRResult[]`` into the very same ``run_scan``.

The image route is pure composition of two services that already existed; it adds no
OCR, extraction or compliance logic of its own, and there is no second pipeline. The
JSON contract of ``POST /scan`` is unchanged.

``run_scan`` never raises: a missing input SKIPs its stage and a stage error is recorded
as FAILED, so a partial ``ScanResult`` is always returned with per-stage coverage in
``stages``/``warnings``.
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.compliance.engine import ComplianceEngine
from app.compliance.rule_loader import RuleLoader
from app.core.enums import ImageQualityStatus, OCRStatus, ProductCategory, StageOutcome
from app.database.connection import get_db
from app.imaging.pipeline import process_scan
from app.pipeline.orchestrator import run_scan
from app.schemas.contracts.context import InspectionContext
from app.schemas.contracts.scan import ScanRequest, ScanResult, ScanStageStatus
from app.schemas.imaging import ScanProcessingResult

router = APIRouter()



def get_compliance_engine(session: Session = Depends(get_db)) -> ComplianceEngine:
    """The production engine: the unchanged ``ComplianceEngine`` over DB-backed rules.

    ``RuleLoader`` satisfies the engine's ``RuleResolver`` protocol and reads the versioned
    legal rules from the database. Construction opens no connection (the session is lazy), so
    a request that supplies no ``context`` skips the legal stage without ever touching the DB;
    and if the DB is unreachable when rules ARE needed, the engine degrades to MANUAL_REVIEW
    rather than raising.
    """

    return ComplianceEngine(RuleLoader(session))


@router.post(
    "/scan",
    response_model=ScanResult,
    summary="Run one label scan through extraction, legal, verification and guidance",
)
def create_scan(
    request: ScanRequest,
    engine: ComplianceEngine = Depends(get_compliance_engine),
) -> ScanResult:
    """Assemble one unified ``ScanResult`` from already-produced OCR/verification inputs.

    Every verdict comes from the layer that owns it: the legal status is the engine's own
    ``ComplianceAssessment``, never restated here. A ``scan_id`` is generated (matching the
    imaging layer's ``uuid4().hex`` convention) when the caller omits one. The call never
    raises on partial input -- unmet stages are SKIPPED and stage errors are recorded as
    FAILED -- so the response always carries per-stage ``stages``.
    """

    return run_scan(
        scan_id=request.scan_id or uuid4().hex,
        ocr_results=request.ocr_results,
        engine=engine,
        context=request.context,
        verification_inputs=request.verification_inputs,
        nutrition=request.nutrition,
        product=request.product,
        ingredients=request.ingredients,
        evidence=request.evidence,
    )


# --------------------------------------------------------------------------- #
# image capture -> the SAME pipeline
# --------------------------------------------------------------------------- #

#: OCR outcome -> how the stage is reported. SUCCESS/LOW_CONFIDENCE/NO_TEXT_DETECTED all
#: mean OCR *ran* (finding no text is a real answer, not a fault); the two error states
#: mean it did not. An OCR fault is an operational failure, never a legal verdict.
_OCR_STAGE_OUTCOME = {
    OCRStatus.SUCCESS: StageOutcome.COMPLETED,
    OCRStatus.LOW_CONFIDENCE: StageOutcome.COMPLETED,
    OCRStatus.NO_TEXT_DETECTED: StageOutcome.COMPLETED,
    OCRStatus.PROCESSING_ERROR: StageOutcome.FAILED,
    OCRStatus.INVALID_IMAGE: StageOutcome.FAILED,
}

_UNREADABLE_LABEL_WARNING = (
    "The label text could not be read reliably from this photo, so declarations that "
    "were not found are marked for manual review rather than treated as omissions."
)

_CAMERA_CANNOT_WEIGH_NOTE = (
    "This scan is based only on information visible on the label. A camera cannot "
    "measure the physical quantity inside a sealed package."
)


def _label_readable(processed: ScanProcessingResult) -> bool | None:
    """Whether the photo genuinely yielded a readable label.

    This is the one lever that separates "not detected" from "omitted" (see
    ``app/pipeline/legal.py``): the engine may report POTENTIAL_NON_COMPLIANCE for a
    missing declaration ONLY when ``label_readable is True``. We claim ``True`` only when
    the real quality report says the image is usable AND OCR actually returned text;
    otherwise we return ``None`` (unknown) so an unread label degrades to MANUAL_REVIEW
    instead of manufacturing violations out of an OCR failure.
    """
    quality_usable = processed.image_quality.status is not ImageQualityStatus.UNUSABLE
    read_text = bool(processed.ocr.regions) and processed.ocr.status in (
        OCRStatus.SUCCESS,
        OCRStatus.LOW_CONFIDENCE,
    )
    return True if (quality_usable and read_text) else None


def _dedupe(lines: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for line in lines:
        if line not in seen:
            seen.add(line)
            out.append(line)
    return out


def _with_image_stages(
    result: ScanResult,
    processed: ScanProcessingResult,
    label_readable: bool | None,
) -> ScanResult:
    """Prepend the real image + OCR stages and merge their warnings.

    Purely additive reporting: no verdict is touched. The image/OCR legs ran before
    ``run_scan``, so they are shown ahead of its own stages.
    """
    image_stage = ScanStageStatus(
        stage="image",
        status=StageOutcome.COMPLETED,
        detail=(
            f"{processed.image_format} {processed.width}x{processed.height}, "
            f"quality={processed.image_quality.status.value}"
        ),
    )
    provider = processed.ocr.provider or "none installed"
    ocr_stage = ScanStageStatus(
        stage="ocr",
        status=_OCR_STAGE_OUTCOME.get(processed.ocr.status, StageOutcome.FAILED),
        detail=(
            f"status={processed.ocr.status.value}, "
            f"{len(processed.ocr.regions)} region(s), provider={provider}"
        ),
    )

    warnings = [*processed.warnings, *processed.ocr.warnings]
    if label_readable is not True:
        warnings.append(_UNREADABLE_LABEL_WARNING)
    warnings.append(_CAMERA_CANNOT_WEIGH_NOTE)
    warnings.extend(result.warnings)

    return result.model_copy(
        update={
            "stages": [image_stage, ocr_stage, *result.stages],
            "warnings": _dedupe(warnings),
        }
    )


@router.post(
    "/scan/image",
    response_model=ScanResult,
    summary="Run one captured label photo through image processing, OCR and the full scan",
)
async def create_scan_from_image(
    image: UploadFile = File(..., description="Photo of the product label (JPEG/PNG/WEBP)."),
    product_category: ProductCategory = Form(
        default=ProductCategory.PACKAGED_FOOD,
        description="Category the label is assessed against.",
    ),
    inspection_datetime: datetime | None = Form(
        default=None, description="Defaults to now (UTC) when omitted."
    ),
    engine: ComplianceEngine = Depends(get_compliance_engine),
) -> ScanResult:
    """Capture-to-result in one call, reusing both existing services unchanged.

    ``process_scan`` owns image intake/validation/quality/preprocessing/OCR; ``run_scan``
    owns extraction/legal/verification/guidance/nutrition. This handler only passes the
    OCR output of the first into the second, so there is exactly one scan pipeline and
    exactly one place each verdict is produced.

    An image that cannot be decoded at all raises ``AppError`` from ``load_scan``, which
    the app's global handler renders as a JSON error envelope (HTTP 4xx). Anything that is
    decodable always returns a ``ScanResult`` — with the image/OCR outcome visible in
    ``stages`` and ``warnings`` — so a failed OCR is reported, never hidden and never
    turned into a compliance claim.
    """

    raw = await image.read()

    # Decoding, preprocessing and OCR are blocking CPU work, so they run in a worker
    # thread instead of stalling the event loop for every other request.
    processed = await run_in_threadpool(
        process_scan, raw, filename=image.filename, content_type=image.content_type
    )

    return scan_from_processed_image(
        processed, engine=engine, product_category=product_category, inspection_datetime=inspection_datetime
    )


def scan_from_processed_image(
    processed: ScanProcessingResult,
    *,
    engine: ComplianceEngine,
    product_category: ProductCategory = ProductCategory.PACKAGED_FOOD,
    inspection_datetime: datetime | None = None,
) -> ScanResult:
    """The image-route body minus HTTP: processed image -> the existing ``run_scan``.

    Split out so the composition is directly testable without a transport layer (the same
    reason the JSON route's tests call ``create_scan`` directly).
    """
    readable = _label_readable(processed)
    context = InspectionContext(
        inspection_datetime=inspection_datetime or datetime.now(timezone.utc),
        product_category=product_category,
        label_readable=readable,
    )

    result = run_scan(
        scan_id=processed.scan_id,
        ocr_results=processed.ocr.regions,
        engine=engine,
        context=context,
    )

    return _with_image_stages(result, processed, readable)
