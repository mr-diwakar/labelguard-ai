"""
PaddleOCR provider (Phase 12).

PaddleOCR is an OPTIONAL, heavy dependency and is intentionally NOT imported at
module top. That keeps the whole imaging/OCR package importable — and the test
suite runnable — on a machine where paddleocr is not installed. The engine is:

- imported lazily, inside `_ensure_engine`;
- constructed once per process per language set (spec §31), cached at module scope;
- probed with `available()` without importing the heavy package.

If paddleocr is missing or fails to construct, `recognize` raises; the OCR service
turns that into an OCRStatus.PROCESSING_ERROR rather than crashing the pipeline.
See docs/scan-ocr.md for the install command.
"""

import importlib
import importlib.util

import numpy as np

from app.core.config import Settings, get_settings
from app.ocr.provider import RawTextRegion

# Engines are expensive to build and safe to reuse, so cache per language tuple.
_ENGINE_CACHE: dict[tuple[str, ...], object] = {}


class PaddleOCRProvider:
    """OCRProvider backed by PaddleOCR. Implements the OCRProvider protocol."""

    def __init__(
        self,
        languages: list[str] | None = None,
        *,
        settings: Settings | None = None,
    ) -> None:
        settings = settings or get_settings()
        self._languages = list(languages or settings.ocr_languages) or ["en"]

    @property
    def name(self) -> str:
        return "paddleocr:" + "+".join(self._languages)

    @classmethod
    def available(cls) -> bool:
        """True if paddleocr can be imported, without actually importing it."""
        return importlib.util.find_spec("paddleocr") is not None

    def _ensure_engine(self) -> object:
        key = tuple(self._languages)
        engine = _ENGINE_CACHE.get(key)
        if engine is not None:
            return engine

        # Lazy, first-use import. PaddleOCR selects a model per single `lang`.
        paddleocr = importlib.import_module("paddleocr")
        lang = self._languages[0]
        try:
            engine = paddleocr.PaddleOCR(use_angle_cls=True, lang=lang, show_log=False)
        except TypeError:
            # Newer PaddleOCR renamed/removed some constructor kwargs; fall back
            # to the minimal signature that is stable across versions.
            engine = paddleocr.PaddleOCR(lang=lang)

        _ENGINE_CACHE[key] = engine
        return engine

    def recognize(self, image: np.ndarray) -> list[RawTextRegion]:
        engine = self._ensure_engine()
        raw = engine.ocr(image, cls=True)
        return _parse_paddle_result(raw)


def _parse_paddle_result(raw: object) -> list[RawTextRegion]:
    """
    Parse PaddleOCR's classic `.ocr(...)` output into RawTextRegions.

    Expected shape: [ [ [box_points, (text, confidence)], ... ] ] where the outer
    list is per-image. Anything unexpected is skipped defensively rather than
    raising, so one odd line never loses the whole read.
    """
    regions: list[RawTextRegion] = []
    if not raw:
        return regions

    # `.ocr` wraps results in a per-image list; unwrap the first (only) image.
    lines = raw[0] if isinstance(raw, (list, tuple)) and raw and isinstance(raw[0], (list, tuple)) else raw
    if not lines:
        return regions

    for entry in lines:
        try:
            box, (text, confidence) = entry
            points = [(float(p[0]), float(p[1])) for p in box]
            regions.append(RawTextRegion(text=str(text), confidence=float(confidence), box=points))
        except (ValueError, TypeError, IndexError):
            continue

    return regions
