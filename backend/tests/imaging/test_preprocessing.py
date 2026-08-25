"""Phase 12: OpenCV preprocessing steps."""

import numpy as np
import pytest

pytest.importorskip("cv2")
pytest.importorskip("numpy")

from app.core.config import Settings
from app.imaging.preprocessing import ImagePreprocessor
from tests.fixtures.images import clear_array


def test_resize_caps_long_edge():
    pre = ImagePreprocessor(Settings(image_preprocess_max_dim=200))
    out = pre.resize_to_max_dim(clear_array(800, 600))
    assert max(out.shape[:2]) == 200
    # aspect ratio preserved (800:600 -> 200:150)
    assert out.shape[:2] == (150, 200)


def test_resize_does_not_upscale_small_images():
    pre = ImagePreprocessor(Settings(image_preprocess_max_dim=2000))
    src = clear_array(400, 300)
    out = pre.resize_to_max_dim(src)
    assert out.shape == src.shape


def test_to_grayscale_returns_single_channel():
    pre = ImagePreprocessor()
    gray = pre.to_grayscale(clear_array(100, 80))
    assert gray.ndim == 2
    assert gray.shape == (80, 100)


def test_prepare_for_ocr_returns_three_channel_uint8():
    pre = ImagePreprocessor()
    out = pre.prepare_for_ocr(clear_array(400, 300))
    assert out.ndim == 3 and out.shape[2] == 3
    assert out.dtype == np.uint8


def test_prepare_for_ocr_respects_max_dim():
    pre = ImagePreprocessor(Settings(image_preprocess_max_dim=256))
    out = pre.prepare_for_ocr(clear_array(1024, 768))
    assert max(out.shape[:2]) == 256


def test_prepare_for_ocr_does_not_mutate_original():
    pre = ImagePreprocessor()
    src = clear_array(400, 300)
    snapshot = src.copy()
    pre.prepare_for_ocr(src)
    assert np.array_equal(src, snapshot)


def test_binarize_is_opt_in_and_produces_binary_values():
    pre = ImagePreprocessor()
    gray = pre.to_grayscale(clear_array(200, 150))
    binary = pre.binarize(gray)
    assert set(np.unique(binary)).issubset({0, 255})
