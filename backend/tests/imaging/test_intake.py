"""Phase 12: scan intake / decoding / EXIF orientation."""

import pytest

pytest.importorskip("cv2")
pytest.importorskip("numpy")

from app.core.enums import OrientationStatus
from app.core.exceptions import AppError
from app.imaging.intake import PreparedImage, load_scan
from tests.fixtures.images import (
    clear_image_bytes,
    corrupted_image_bytes,
    empty_bytes,
    image_with_exif_orientation,
    not_an_image_bytes,
)


def test_load_scan_decodes_to_bgr_array():
    prepared = load_scan(clear_image_bytes("PNG", 800, 600))
    assert isinstance(prepared, PreparedImage)
    assert prepared.image_format == "PNG"
    assert prepared.width == 800
    assert prepared.height == 600
    assert prepared.bgr.shape == (600, 800, 3)


def test_load_scan_generates_unique_scan_ids():
    a = load_scan(clear_image_bytes("PNG"))
    b = load_scan(clear_image_bytes("PNG"))
    assert a.scan_id and b.scan_id
    assert a.scan_id != b.scan_id


def test_load_scan_reports_upright_orientation_without_exif():
    prepared = load_scan(clear_image_bytes("PNG"))
    assert prepared.orientation.status is OrientationStatus.OK
    assert prepared.orientation.rotation_applied == 0


def test_load_scan_applies_exif_orientation():
    # orientation 6 (rotate 90° CW) -> exif_transpose swaps width/height.
    data = image_with_exif_orientation(orientation=6, width=480, height=360)
    prepared = load_scan(data)
    assert prepared.orientation.status is OrientationStatus.CORRECTED
    assert prepared.orientation.rotation_applied == 90
    # The upright image is portrait after correcting a landscape capture.
    assert prepared.width == 360
    assert prepared.height == 480


def test_load_scan_does_not_mutate_input_bytes():
    data = clear_image_bytes("PNG")
    original = bytes(data)
    load_scan(data)
    assert data == original


def test_load_scan_rejects_empty():
    with pytest.raises(AppError) as exc:
        load_scan(empty_bytes())
    assert exc.value.code == "EMPTY_IMAGE"


def test_load_scan_rejects_corrupted():
    with pytest.raises(AppError) as exc:
        load_scan(corrupted_image_bytes())
    assert exc.value.code == "CORRUPTED_IMAGE"


def test_load_scan_rejects_unsupported():
    with pytest.raises(AppError) as exc:
        load_scan(not_an_image_bytes())
    assert exc.value.code == "UNSUPPORTED_FORMAT"


def test_filename_hint_is_ignored_for_format():
    # A misleading filename does not change the detected format.
    prepared = load_scan(clear_image_bytes("PNG"), filename="photo.jpg", content_type="image/jpeg")
    assert prepared.image_format == "PNG"
