"""
Phase 12: integration with the Phase 11 OCR contract (spec §6).

Guarantees the scan pipeline emits the *existing* contract types and that no second
OCR result model was introduced.
"""

import typing

import pytest

pytest.importorskip("cv2")
pytest.importorskip("numpy")

from app.imaging.pipeline import process_scan
from app.imaging.quality import assess_quality
from app.imaging.intake import PreparedImage
from app.core.enums import OrientationStatus
from app.ocr.provider import RawTextRegion
from app.schemas.imaging import OCRResponse, OrientationResult
from app.schemas.ocr import ImageQualityResult, OCRResult
from tests.fixtures.images import StubOCRProvider, clear_array, clear_image_bytes


def test_pipeline_regions_are_phase11_ocrresult():
    provider = StubOCRProvider(
        [RawTextRegion(text="MRP 50", confidence=0.9, box=[(10, 10), (100, 10), (100, 40), (10, 40)])]
    )
    result = process_scan(clear_image_bytes("PNG"), provider=provider)
    assert result.ocr.regions
    for region in result.ocr.regions:
        assert isinstance(region, OCRResult)


def test_ocrresponse_reuses_ocrresult_type():
    # The container references the Phase 11 model directly (no parallel model).
    hints = typing.get_type_hints(OCRResponse)
    assert hints["regions"] == list[OCRResult]


def test_quality_report_adapts_to_phase11_quality_result():
    prepared = PreparedImage(
        scan_id="t",
        image_format="PNG",
        bgr=clear_array(),
        width=800,
        height=600,
        orientation=OrientationResult(status=OrientationStatus.OK),
    )
    thin = assess_quality(prepared).to_image_quality_result()
    assert isinstance(thin, ImageQualityResult)


def test_produced_ocrresult_satisfies_contract_invariants():
    provider = StubOCRProvider(
        [RawTextRegion(text="NET 100 g", confidence=0.8, box=[(5, 5), (90, 5), (90, 30), (5, 30)])]
    )
    result = process_scan(clear_image_bytes("PNG"), provider=provider)
    region = result.ocr.regions[0]
    x1, y1, x2, y2 = region.bbox
    assert x2 >= x1 and y2 >= y1
    assert 0.0 <= region.confidence <= 1.0
    assert isinstance(region.text, str)
