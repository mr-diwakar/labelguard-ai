"""Phase 12: normalization of raw OCR regions to the Phase 11 OCRResult contract."""

import pytest

from app.core.enums import OCRStatus
from app.ocr.normalization import build_ocr_response, normalize_region, to_bbox
from app.ocr.provider import RawTextRegion
from app.schemas.ocr import OCRResult

_SQUARE = [(10.0, 20.0), (110.0, 20.0), (110.0, 60.0), (10.0, 60.0)]


def test_to_bbox_encloses_polygon_and_is_ordered():
    assert to_bbox(_SQUARE) == [10, 20, 110, 60]


def test_to_bbox_handles_unordered_points():
    reversed_pts = list(reversed(_SQUARE))
    bbox = to_bbox(reversed_pts)
    assert bbox == [10, 20, 110, 60]
    x1, y1, x2, y2 = bbox
    assert x2 >= x1 and y2 >= y1


def test_to_bbox_clamps_negative_and_bounds():
    pts = [(-5.0, -8.0), (50.0, 50.0)]
    assert to_bbox(pts, width=40, height=40) == [0, 0, 40, 40]


def test_to_bbox_empty_polygon():
    assert to_bbox([]) == [0, 0, 0, 0]


def test_normalize_region_clamps_confidence_and_strips_text():
    high = normalize_region(RawTextRegion(text="  MRP 50 \n", confidence=1.4, box=_SQUARE))
    assert isinstance(high, OCRResult)
    assert high.text == "MRP 50"
    assert high.confidence == 1.0

    low = normalize_region(RawTextRegion(text="x", confidence=-0.2, box=_SQUARE))
    assert low.confidence == 0.0


def test_build_response_no_regions_is_no_text_detected():
    resp = build_ocr_response([], low_confidence_threshold=0.5)
    assert resp.status is OCRStatus.NO_TEXT_DETECTED
    assert resp.regions == []
    assert resp.mean_confidence is None


def test_build_response_drops_blank_regions():
    resp = build_ocr_response(
        [RawTextRegion(text="   ", confidence=0.9, box=_SQUARE)],
        low_confidence_threshold=0.5,
    )
    assert resp.status is OCRStatus.NO_TEXT_DETECTED


def test_build_response_success_when_confident():
    resp = build_ocr_response(
        [
            RawTextRegion(text="MRP 50", confidence=0.9, box=_SQUARE),
            RawTextRegion(text="NET 100 g", confidence=0.8, box=_SQUARE),
        ],
        low_confidence_threshold=0.5,
        provider="stub",
        languages=["en"],
    )
    assert resp.status is OCRStatus.SUCCESS
    assert len(resp.regions) == 2
    assert resp.provider == "stub"
    assert resp.languages == ["en"]
    assert resp.mean_confidence == pytest.approx(0.85)


def test_build_response_low_confidence_at_or_below_threshold():
    resp = build_ocr_response(
        [RawTextRegion(text="blurry", confidence=0.4, box=_SQUARE)],
        low_confidence_threshold=0.5,
    )
    assert resp.status is OCRStatus.LOW_CONFIDENCE


def test_text_is_preserved_verbatim_not_interpreted():
    # Phase 12 must not parse "MRP ₹50" into a value; the string is kept as-is.
    resp = build_ocr_response(
        [RawTextRegion(text="MRP ₹50", confidence=0.95, box=_SQUARE)],
        low_confidence_threshold=0.5,
    )
    assert resp.regions[0].text == "MRP ₹50"
