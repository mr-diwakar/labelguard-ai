"""Phase 12: image quality metrics and the usability heuristic."""

import pytest

pytest.importorskip("cv2")
pytest.importorskip("numpy")

from app.core.config import get_settings
from app.core.enums import (
    BrightnessStatus,
    ImageQualityStatus,
    OrientationStatus,
    ResolutionStatus,
)
from app.imaging.intake import PreparedImage
from app.imaging.quality import assess_quality, classify_quality
from app.schemas.imaging import (
    BlurResult,
    BrightnessResult,
    OrientationResult,
    ResolutionResult,
)
from tests.fixtures.images import blurry_array, clear_array, flat_array


def _prepared(arr, orientation=None):
    return PreparedImage(
        scan_id="test",
        image_format="PNG",
        bgr=arr,
        width=arr.shape[1],
        height=arr.shape[0],
        orientation=orientation or OrientationResult(status=OrientationStatus.OK),
    )


# --- classify_quality (pure, hand-built inputs) ----------------------------

_GOOD_BLUR = BlurResult(is_blurry=False, score=400.0, threshold=100.0)
_GOOD_BRIGHT = BrightnessResult(status=BrightnessStatus.ACCEPTABLE, mean=150, min_threshold=40, max_threshold=220)
_GOOD_RES = ResolutionResult(width=800, height=600, min_width=320, min_height=320, status=ResolutionStatus.OK)
_OK_ORIENT = OrientationResult(status=OrientationStatus.OK)


def test_classify_all_good_is_ok():
    settings = get_settings()
    status, warnings = classify_quality(_GOOD_BLUR, _GOOD_BRIGHT, _GOOD_RES, _OK_ORIENT, settings=settings)
    assert status is ImageQualityStatus.OK
    assert warnings == []


def test_classify_single_mild_problem_is_warning():
    settings = get_settings()
    mild_blur = BlurResult(is_blurry=True, score=80.0, threshold=100.0)  # 80 > 50 -> not severe
    status, warnings = classify_quality(mild_blur, _GOOD_BRIGHT, _GOOD_RES, _OK_ORIENT, settings=settings)
    assert status is ImageQualityStatus.WARNING
    assert warnings


def test_classify_severe_blur_is_unusable():
    settings = get_settings()
    severe = BlurResult(is_blurry=True, score=10.0, threshold=100.0)  # < 50 -> severe
    status, _ = classify_quality(severe, _GOOD_BRIGHT, _GOOD_RES, _OK_ORIENT, settings=settings)
    assert status is ImageQualityStatus.UNUSABLE


def test_classify_two_problems_is_unusable():
    settings = get_settings()
    mild_blur = BlurResult(is_blurry=True, score=80.0, threshold=100.0)
    dark = BrightnessResult(status=BrightnessStatus.TOO_DARK, mean=10, min_threshold=40, max_threshold=220)
    status, _ = classify_quality(mild_blur, dark, _GOOD_RES, _OK_ORIENT, settings=settings)
    assert status is ImageQualityStatus.UNUSABLE


def test_classify_unknown_orientation_is_warning_only():
    settings = get_settings()
    unknown = OrientationResult(status=OrientationStatus.UNKNOWN)
    status, warnings = classify_quality(_GOOD_BLUR, _GOOD_BRIGHT, _GOOD_RES, unknown, settings=settings)
    assert status is ImageQualityStatus.WARNING  # advisory, never blocks OCR
    assert any("orientation" in w.lower() for w in warnings)


# --- assess_quality (real images) ------------------------------------------


def test_assess_clear_image_is_ok():
    report = assess_quality(_prepared(clear_array()))
    assert report.status is ImageQualityStatus.OK
    assert report.blur.is_blurry is False
    assert report.brightness.status is BrightnessStatus.ACCEPTABLE
    assert report.resolution.status is ResolutionStatus.OK


def test_assess_blurry_image_flags_blur():
    report = assess_quality(_prepared(blurry_array()))
    assert report.blur.is_blurry is True


def test_assess_flat_image_is_unusable():
    report = assess_quality(_prepared(flat_array()))
    assert report.status is ImageQualityStatus.UNUSABLE


def test_assess_low_resolution_flags_too_small():
    small = clear_array(120, 120)
    report = assess_quality(_prepared(small))
    assert report.resolution.status is ResolutionStatus.TOO_SMALL


# --- down-adapter to the Phase 11 contract ---------------------------------


def test_unusable_maps_to_not_usable():
    report = assess_quality(_prepared(flat_array()))
    thin = report.to_image_quality_result()
    assert thin.usable is False
    assert thin.reason


def test_ok_maps_to_usable():
    report = assess_quality(_prepared(clear_array()))
    thin = report.to_image_quality_result()
    assert thin.usable is True
    assert thin.reason is None
