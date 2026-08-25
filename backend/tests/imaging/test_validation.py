"""Phase 12: byte-level image validation."""

import pytest

pytest.importorskip("cv2")
pytest.importorskip("numpy")

from app.core.config import Settings, get_settings
from app.core.exceptions import AppError
from app.imaging.validation import detect_format, ensure_dimensions, ensure_supported
from tests.fixtures.images import (
    clear_image_bytes,
    corrupted_image_bytes,
    empty_bytes,
    not_an_image_bytes,
    oversized_bytes,
)


def test_detect_format_from_magic_bytes():
    assert detect_format(clear_image_bytes("JPEG")) == "JPEG"
    assert detect_format(clear_image_bytes("PNG")) == "PNG"
    assert detect_format(clear_image_bytes("WEBP")) == "WEBP"


def test_detect_format_rejects_non_image():
    assert detect_format(not_an_image_bytes()) is None
    assert detect_format(b"") is None


def test_format_is_not_trusted_from_extension():
    # A PDF is a PDF regardless of any (unused) filename hint.
    assert detect_format(not_an_image_bytes()) is None


def test_ensure_supported_accepts_known_formats():
    settings = get_settings()
    assert ensure_supported(clear_image_bytes("PNG"), settings) == "PNG"
    assert ensure_supported(clear_image_bytes("JPEG"), settings) == "JPEG"


def test_ensure_supported_rejects_empty():
    with pytest.raises(AppError) as exc:
        ensure_supported(empty_bytes(), get_settings())
    assert exc.value.code == "EMPTY_IMAGE"
    assert exc.value.status_code == 422


def test_ensure_supported_rejects_oversized():
    settings = Settings(scan_max_file_bytes=1024)
    with pytest.raises(AppError) as exc:
        ensure_supported(oversized_bytes(4096), settings)
    assert exc.value.code == "IMAGE_TOO_LARGE"
    assert exc.value.status_code == 413


def test_ensure_supported_rejects_unsupported_format():
    with pytest.raises(AppError) as exc:
        ensure_supported(not_an_image_bytes(), get_settings())
    assert exc.value.code == "UNSUPPORTED_FORMAT"
    assert exc.value.status_code == 415


def test_corrupted_image_still_has_valid_signature():
    # Sniffing passes (it is a PNG signature); the decode-stage check catches it.
    assert detect_format(corrupted_image_bytes()) == "PNG"


def test_ensure_dimensions_rejects_zero_and_too_large():
    settings = get_settings()
    with pytest.raises(AppError) as exc:
        ensure_dimensions(0, 100, settings)
    assert exc.value.code == "INVALID_DIMENSIONS"

    with pytest.raises(AppError):
        ensure_dimensions(settings.image_max_width + 1, 100, settings)


def test_ensure_dimensions_accepts_normal():
    ensure_dimensions(800, 600, get_settings())  # must not raise
