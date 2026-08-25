"""
Phase 12: end-to-end scan pipeline (process_scan) + error handling + scope guards.

Scope guards encode the spec's hard boundaries: the pipeline produces IMAGE +
QUALITY + OCR only, never a compliance decision, and NO_TEXT_DETECTED is never a
"missing declaration". A source-level check also proves the imaging/OCR packages do
not import the legal engine or the database layer.
"""

from pathlib import Path

import pytest

pytest.importorskip("cv2")
pytest.importorskip("numpy")

from app.core.enums import ImageQualityStatus, OCRStatus
from app.core.exceptions import AppError
from app.imaging.pipeline import process_scan
from app.ocr.provider import RawTextRegion
from app.schemas.imaging import ScanProcessingResult
from tests.fixtures.images import (
    StubOCRProvider,
    clear_image_bytes,
    corrupted_image_bytes,
    empty_bytes,
    flat_array,
    not_an_image_bytes,
)
from tests.fixtures.images import encode as _encode

_REGION = RawTextRegion(text="MRP 50", confidence=0.9, box=[(20, 20), (200, 20), (200, 60), (20, 60)])


def test_process_scan_returns_quality_and_ocr():
    provider = StubOCRProvider([_REGION], name="stub")
    result = process_scan(clear_image_bytes("PNG", 800, 600), provider=provider)
    assert isinstance(result, ScanProcessingResult)
    assert result.scan_id
    assert result.image_format == "PNG"
    assert result.width == 800 and result.height == 600
    # BOTH signals preserved (spec §22).
    assert result.image_quality is not None
    assert result.ocr.status is OCRStatus.SUCCESS
    assert result.ocr.regions[0].text == "MRP 50"


def test_process_scan_rejects_bad_inputs():
    provider = StubOCRProvider([_REGION])
    for data, code in [
        (empty_bytes(), "EMPTY_IMAGE"),
        (corrupted_image_bytes(), "CORRUPTED_IMAGE"),
        (not_an_image_bytes(), "UNSUPPORTED_FORMAT"),
    ]:
        with pytest.raises(AppError) as exc:
            process_scan(data, provider=provider)
        assert exc.value.code == code


def test_process_scan_without_provider_reports_processing_error():
    # No provider injected and PaddleOCR not installed -> graceful, no crash.
    result = process_scan(clear_image_bytes("PNG"), provider=None)
    assert result.ocr.status is OCRStatus.PROCESSING_ERROR
    assert result.ocr.warnings
    # Quality is still computed independently of the OCR failure.
    assert result.image_quality is not None


def test_quality_and_ocr_are_independent():
    # An UNUSABLE image still goes through OCR; a good OCR read does not "fix"
    # the quality verdict, and a bad quality verdict does not block OCR.
    provider = StubOCRProvider([_REGION])
    result = process_scan(_encode(flat_array(800, 600), "PNG"), provider=provider)
    assert result.image_quality.status is ImageQualityStatus.UNUSABLE
    assert result.ocr.status is OCRStatus.SUCCESS


def test_no_text_detected_is_not_a_missing_declaration():
    empty_provider = StubOCRProvider([], name="stub")
    result = process_scan(clear_image_bytes("PNG"), provider=empty_provider)
    assert result.ocr.status is OCRStatus.NO_TEXT_DETECTED
    # The result carries no compliance / declaration verdict of any kind.
    assert not hasattr(result, "compliance")
    assert not hasattr(result, "declarations")


def test_imaging_and_ocr_packages_do_not_import_legal_engine():
    root = Path(__file__).resolve().parents[2] / "app"
    forbidden = ("app.compliance", "app.database", "ComplianceStatus", "DeclarationStatus")
    for package in ("imaging", "ocr"):
        for path in (root / package).glob("*.py"):
            source = path.read_text(encoding="utf-8")
            for token in forbidden:
                assert token not in source, f"{path.name} references forbidden {token!r}"
