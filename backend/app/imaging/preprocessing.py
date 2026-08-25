"""
OpenCV preprocessing for OCR (Phase 12).

A small, composable set of steps. Each returns a NEW array and never mutates its
input, so `PreparedImage.bgr` (derived from the untouched original bytes) is
preserved (spec §15). `prepare_for_ocr` chains the default steps and returns a
3-channel BGR image so the OCR provider does not need to care how it was enhanced.

Binarization is deliberately opt-in: modern detectors usually do better on the
natural (contrast-enhanced) image than on a hard threshold, so it is off by default.
"""

import cv2
import numpy as np

from app.core.config import Settings, get_settings


class ImagePreprocessor:
    """Stateless-per-call preprocessing configured from `Settings`."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def resize_to_max_dim(self, image: np.ndarray) -> np.ndarray:
        """Downscale so the long edge is at most `image_preprocess_max_dim`."""
        max_dim = self._settings.image_preprocess_max_dim
        height, width = image.shape[:2]
        longest = max(height, width)
        if longest <= max_dim:
            return image.copy()
        scale = max_dim / float(longest)
        new_size = (max(1, int(round(width * scale))), max(1, int(round(height * scale))))
        # INTER_AREA is the correct interpolation for shrinking.
        return cv2.resize(image, new_size, interpolation=cv2.INTER_AREA)

    def to_grayscale(self, image: np.ndarray) -> np.ndarray:
        if image.ndim == 2:
            return image.copy()
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    def enhance_contrast(self, gray: np.ndarray) -> np.ndarray:
        """CLAHE — local contrast boost that helps faded/uneven label print."""
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        return clahe.apply(gray)

    def denoise(self, gray: np.ndarray) -> np.ndarray:
        """Light edge-preserving smoothing to suppress sensor/JPEG noise."""
        return cv2.medianBlur(gray, 3)

    def binarize(self, gray: np.ndarray) -> np.ndarray:
        """Adaptive (Gaussian) threshold. Opt-in; not part of the default chain."""
        return cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, blockSize=31, C=10
        )

    def prepare_for_ocr(self, image: np.ndarray, *, binarize: bool = False) -> np.ndarray:
        """
        Default OCR-preparation chain: resize -> grayscale -> CLAHE -> denoise
        (-> optional binarize) -> back to 3-channel BGR.

        Returns a fresh array; `image` is left untouched.
        """
        working = self.resize_to_max_dim(image)
        gray = self.to_grayscale(working)
        gray = self.enhance_contrast(gray)
        gray = self.denoise(gray)
        if binarize:
            gray = self.binarize(gray)
        return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
