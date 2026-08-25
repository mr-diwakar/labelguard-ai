"""The camera flow, end to end: a real image -> OCR -> ``OCRResult[]`` -> ``run_scan``.

This is the integration/smoke suite for ``POST /scan/image``. It drives a genuinely
encoded PNG through the REAL ``process_scan`` (intake, magic-byte validation, quality,
preprocessing, OCR service) and feeds its real ``OCRResult`` list into the REAL
``scan_from_processed_image`` -> ``run_scan``. Nothing about the image path, the OCR
normalization, the extraction, or the assessment is stubbed.

The ONE test double is ``StubOCRProvider`` standing in for the third-party recognition
engine, which has no distribution for this interpreter (see
``tests/imaging/test_scan_pipeline.py``, which uses it the same way). It supplies the raw
engine output only; the real ``OCRService`` normalizes that into ``OCRResult`` objects.
The environment's actual no-engine behaviour is asserted separately below, so an OCR that
cannot run is proven to degrade honestly rather than to be papered over.

The safety invariant under test: an unread label must NEVER become a violation. A photo
whose text could not be read reliably yields ``label_readable=None``, which
``app/pipeline/legal.py`` turns into MANUAL_REVIEW -- never POTENTIAL_NON_COMPLIANCE and
never COMPLIANT.
"""

from datetime import datetime, timezone

import pytest

pytest.importorskip("cv2")
pytest.importorskip("numpy")

from app.api.scan import router, scan_from_processed_image
from app.core.enums import ComplianceStatus, ImageQualityStatus, OCRStatus, StageOutcome
from app.core.exceptions import AppError
from app.imaging.pipeline import process_scan
from app.ocr.paddle_adapter import PaddleOCRProvider
from app.ocr.provider import RawTextRegion
from app.schemas.contracts.scan import ScanResult
from app.schemas.ocr import OCRResult
from tests.fixtures.images import (
    StubOCRProvider,
    clear_image_bytes,
    corrupted_image_bytes,
    encode,
    flat_array,
)
from tests.fixtures.inspections import engine as make_engine
from tests.fixtures.rules import mrp_rule, net_quantity_rule

INSPECTION_AT = datetime(2026, 8, 23, 10, 0, tzinfo=timezone.utc)

# What the recognition engine "saw" on the label. Same declarations the JSON-route tests
# use, so the two entry points are demonstrably assessed by the same code.
_LABEL_REGIONS = [
    RawTextRegion(text="MRP ₹50", confidence=0.94, box=[(20, 20), (300, 20), (300, 70), (20, 70)]),
    RawTextRegion(
        text="Net Quantity 500 g", confidence=0.91, box=[(20, 100), (380, 100), (380, 150), (20, 150)]
    ),
]


def _engine():
    return make_engine([mrp_rule(), net_quantity_rule()])


def _stage_map(scan: ScanResult) -> dict[str, StageOutcome]:
    return {s.stage: s.status for s in scan.stages}


# --------------------------------------------------------------------------- #
# route registration
# --------------------------------------------------------------------------- #


def test_scan_image_route_is_registered_as_post():
    registered = {(tuple(sorted(r.methods)), r.path) for r in router.routes}
    assert (("POST",), "/scan/image") in registered
    # The pre-existing JSON contract is still there, unchanged, alongside it.
    assert (("POST",), "/scan") in registered


# --------------------------------------------------------------------------- #
# the flow: image -> OCR -> OCRResult[] -> run_scan -> ScanResult
# --------------------------------------------------------------------------- #


def test_captured_photo_produces_a_scan_result_through_the_existing_pipeline():
    photo = clear_image_bytes("PNG", 800, 600)

    processed = process_scan(
        photo,
        filename="label.png",
        content_type="image/png",
        provider=StubOCRProvider(_LABEL_REGIONS, name="stub"),
    )

    # --- the image leg really ran on the real bytes (format from magic bytes) ---
    assert processed.image_format == "PNG"
    assert (processed.width, processed.height) == (800, 600)
    assert processed.image_quality.status is ImageQualityStatus.OK
    assert processed.ocr.status is OCRStatus.SUCCESS

    # --- the hand-off is exactly run_scan's input type, built by the OCR layer ---
    assert processed.ocr.regions
    assert all(isinstance(region, OCRResult) for region in processed.ocr.regions)

    result = scan_from_processed_image(processed, engine=_engine(), inspection_datetime=INSPECTION_AT)

    # --- the scan leg ran on what the photo produced ---
    assert isinstance(result, ScanResult)
    assert result.scan_id == processed.scan_id  # one scan id from intake to result
    extracted = {d.field for d in result.declarations}
    assert {"mrp", "net_quantity"} <= extracted  # read off the photo, not injected
    assert result.legal_assessment is not None
    assert result.legal_assessment.status is ComplianceStatus.COMPLIANT
    assert result.guidance is not None

    # --- the image/OCR legs are reported ahead of run_scan's own stages ---
    assert [s.stage for s in result.stages[:2]] == ["image", "ocr"]
    stages = _stage_map(result)
    assert stages["image"] is StageOutcome.COMPLETED
    assert stages["ocr"] is StageOutcome.COMPLETED
    assert stages["extraction"] is StageOutcome.COMPLETED
    assert stages["legal"] is StageOutcome.COMPLETED


def test_result_never_claims_the_camera_measured_the_package_contents():
    processed = process_scan(clear_image_bytes("PNG"), provider=StubOCRProvider(_LABEL_REGIONS))
    result = scan_from_processed_image(processed, engine=_engine(), inspection_datetime=INSPECTION_AT)

    assert any("cannot" in w and "quantity" in w for w in result.warnings)


# --------------------------------------------------------------------------- #
# an unread label degrades to manual review; it never manufactures violations
# --------------------------------------------------------------------------- #


def test_ocr_failure_yields_manual_review_not_non_compliance():
    # Engine present but it blows up mid-recognition -> the real OCRService maps that to
    # PROCESSING_ERROR. Extraction still runs on an empty region list, so without the
    # label_readable guard every required declaration would read as an omission.
    processed = process_scan(
        clear_image_bytes("PNG"), provider=StubOCRProvider(raises=RuntimeError("engine crashed"))
    )
    assert processed.ocr.status is OCRStatus.PROCESSING_ERROR

    result = scan_from_processed_image(processed, engine=_engine(), inspection_datetime=INSPECTION_AT)

    assert _stage_map(result)["ocr"] is StageOutcome.FAILED
    assert result.legal_assessment is not None
    assert result.legal_assessment.status is ComplianceStatus.MANUAL_REVIEW
    assert result.legal_assessment.status is not ComplianceStatus.POTENTIAL_NON_COMPLIANCE
    assert any("manual review" in w.lower() for w in result.warnings)


@pytest.mark.skipif(
    PaddleOCRProvider.available(), reason="an OCR engine is installed, so the photo can be read"
)
def test_no_installed_ocr_engine_is_reported_not_hidden():
    # The actual state of this environment: no recognition engine, so a real photo cannot
    # be read. That must surface as a failed OCR stage plus a manual-review verdict.
    processed = process_scan(clear_image_bytes("PNG"), provider=None)
    assert processed.ocr.status is OCRStatus.PROCESSING_ERROR
    assert processed.ocr.regions == []

    result = scan_from_processed_image(processed, engine=_engine(), inspection_datetime=INSPECTION_AT)

    ocr_stage = next(s for s in result.stages if s.stage == "ocr")
    assert ocr_stage.status is StageOutcome.FAILED
    assert "none installed" in (ocr_stage.detail or "")
    assert result.legal_assessment.status is ComplianceStatus.MANUAL_REVIEW


def test_declaration_missing_from_an_unusable_photo_is_manual_review_not_a_violation():
    # Only the MRP line was recognised; the net-quantity rule has nothing to check. What
    # that means depends entirely on whether the photo was readable, so assert both sides
    # of the same lever -- otherwise the guard could be vacuous and the test still pass.
    mrp_only = [_LABEL_REGIONS[0]]

    unusable = process_scan(encode(flat_array(800, 600), "PNG"), provider=StubOCRProvider(mrp_only))
    assert unusable.image_quality.status is ImageQualityStatus.UNUSABLE
    unusable_result = scan_from_processed_image(
        unusable, engine=_engine(), inspection_datetime=INSPECTION_AT
    )

    readable = process_scan(clear_image_bytes("PNG", 800, 600), provider=StubOCRProvider(mrp_only))
    assert readable.image_quality.status is ImageQualityStatus.OK
    readable_result = scan_from_processed_image(
        readable, engine=_engine(), inspection_datetime=INSPECTION_AT
    )

    # Same missing declaration, opposite readings of it.
    assert unusable_result.legal_assessment.status is ComplianceStatus.MANUAL_REVIEW
    assert readable_result.legal_assessment.status is ComplianceStatus.POTENTIAL_NON_COMPLIANCE

    # The image leg itself completed in both cases -- it reported a problem, it did not fail.
    assert _stage_map(unusable_result)["image"] is StageOutcome.COMPLETED


def test_undecodable_photo_raises_app_error_instead_of_a_fabricated_result():
    # Handled by the app's global AppError handler as a JSON error envelope; the client
    # gets an error, never an empty scan dressed up as a finished one.
    with pytest.raises(AppError) as exc:
        process_scan(corrupted_image_bytes(), filename="label.png", content_type="image/png")
    assert exc.value.code == "CORRUPTED_IMAGE"
