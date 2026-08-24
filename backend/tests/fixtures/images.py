"""
Deterministic image fixtures for Phase 12 tests.

Everything here is generated in-memory with numpy + OpenCV (and Pillow for EXIF),
so tests never touch the filesystem or the network and never depend on PaddleOCR.
Import these from tests as `from tests.fixtures.images import clear_image_bytes`.
"""

from io import BytesIO

import cv2
import numpy as np
from PIL import Image

from app.ocr.provider import RawTextRegion

_EXT = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}


# --- array builders --------------------------------------------------------


def text_document(width: int = 800, height: int = 600, bg: int = 200, fg: int = 0) -> np.ndarray:
    """A BGR page with several lines of text — sharp edges, controllable brightness."""
    img = np.full((height, width, 3), bg, np.uint8)
    line = 0
    for y in range(50, height - 20, 55):
        cv2.putText(
            img,
            f"LABEL LINE {line} MRP 50 NET 100 g",
            (20, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            (fg, fg, fg),
            2,
        )
        line += 1
    return img


def clear_array(width: int = 800, height: int = 600) -> np.ndarray:
    return text_document(width, height, bg=200, fg=0)


def blurry_array(width: int = 800, height: int = 600) -> np.ndarray:
    """Heavily Gaussian-blurred document: low Laplacian variance."""
    return cv2.GaussianBlur(clear_array(width, height), (25, 25), 0)


def flat_array(width: int = 800, height: int = 600, value: int = 128) -> np.ndarray:
    """A uniform image: zero edge energy (maximally 'blurry')."""
    return np.full((height, width, 3), value, np.uint8)


# --- encoding --------------------------------------------------------------


def encode(img: np.ndarray, fmt: str = "PNG") -> bytes:
    ok, buf = cv2.imencode(_EXT[fmt], img)
    if not ok:
        raise RuntimeError(f"failed to encode test image as {fmt}")
    return buf.tobytes()


def clear_image_bytes(fmt: str = "PNG", width: int = 800, height: int = 600) -> bytes:
    return encode(clear_array(width, height), fmt)


def blurry_image_bytes(fmt: str = "PNG", width: int = 800, height: int = 600) -> bytes:
    return encode(blurry_array(width, height), fmt)


def low_res_image_bytes(fmt: str = "PNG") -> bytes:
    return encode(clear_array(120, 120), fmt)


def large_image_bytes(fmt: str = "PNG", width: int = 3000, height: int = 1500) -> bytes:
    return encode(clear_array(width, height), fmt)


# --- malformed / non-image inputs ------------------------------------------


def empty_bytes() -> bytes:
    return b""


def corrupted_image_bytes() -> bytes:
    """Valid PNG signature followed by junk — passes format sniffing, fails decode."""
    return b"\x89PNG\r\n\x1a\n" + bytes(64)


def not_an_image_bytes() -> bytes:
    return b"%PDF-1.4\nnot really an image\n"


def oversized_bytes(size: int) -> bytes:
    """A JPEG-signed blob of a given size, for exercising the size limit cheaply."""
    return b"\xff\xd8\xff" + bytes(max(0, size - 3))


# --- EXIF orientation ------------------------------------------------------


def image_with_exif_orientation(orientation: int = 6, width: int = 480, height: int = 360) -> bytes:
    """A JPEG carrying an EXIF orientation tag (274). 6 = rotate 90° CW."""
    arr = clear_array(width, height)
    pil = Image.fromarray(cv2.cvtColor(arr, cv2.COLOR_BGR2RGB))
    exif = pil.getexif()
    exif[274] = orientation
    bio = BytesIO()
    pil.save(bio, format="JPEG", exif=exif)
    return bio.getvalue()


# --- stub OCR provider -----------------------------------------------------


class StubOCRProvider:
    """A configurable OCRProvider for tests. Implements the OCRProvider protocol."""

    def __init__(
        self,
        regions: list[RawTextRegion] | None = None,
        *,
        name: str = "stub",
        raises: Exception | None = None,
    ) -> None:
        self._regions = regions or []
        self._name = name
        self._raises = raises
        self.calls: list[tuple[int, int]] = []  # (width, height) of each image seen

    @property
    def name(self) -> str:
        return self._name

    def recognize(self, image) -> list[RawTextRegion]:
        h, w = image.shape[:2]
        self.calls.append((w, h))
        if self._raises is not None:
            raise self._raises
        return list(self._regions)
