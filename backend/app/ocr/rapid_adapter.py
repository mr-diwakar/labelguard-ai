"""
RapidOCR provider.

PaddleOCR remains the preferred engine (see ``paddle_adapter.py``). RapidOCR is a
real ONNX PP-OCR reader used only when ``paddleocr`` cannot be imported — which is
the case on Python 3.14 / Windows, where PaddlePaddle has no wheel. It is not a
mock and never invents text.

The package is imported lazily, the same way as PaddleOCR, so the app and the
test suite stay importable when RapidOCR is not installed.
"""

from __future__ import annotations

import importlib
import importlib.util

import numpy as np

from app.core.config import Settings, get_settings
from app.ocr.provider import RawTextRegion

_ENGINE: object | None = None


class RapidOCRProvider:
    """OCRProvider backed by RapidOCR (ONNX PP-OCR). Implements the OCRProvider protocol."""

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
        return "rapidocr:" + "+".join(self._languages)

    @classmethod
    def available(cls) -> bool:
        """True if a RapidOCR package can be imported, without actually importing it."""
        return (
            importlib.util.find_spec("rapidocr") is not None
            or importlib.util.find_spec("rapidocr_onnxruntime") is not None
        )

    def _ensure_engine(self) -> object:
        global _ENGINE
        if _ENGINE is not None:
            return _ENGINE

        try:
            module = importlib.import_module("rapidocr")
        except ImportError:
            module = importlib.import_module("rapidocr_onnxruntime")

        engine_cls = getattr(module, "RapidOCR")
        _ENGINE = engine_cls()
        return _ENGINE

    def recognize(self, image: np.ndarray) -> list[RawTextRegion]:
        engine = self._ensure_engine()
        raw = engine(image)
        return _parse_rapid_result(raw)


def _parse_rapid_result(raw: object) -> list[RawTextRegion]:
    """
    Parse RapidOCR output into RawTextRegions.

    Supported shapes:
    - RapidOCR 2.x object with ``boxes`` / ``txts`` / ``scores``
    - ``(result_list, elapse)`` where each item is ``[box, text, score]``
    - a bare list of ``[box, text, score]``
    Unexpected entries are skipped so one odd line never loses the whole read.
    """
    if raw is None:
        return []

    boxes = getattr(raw, "boxes", None)
    texts = getattr(raw, "txts", None)
    scores = getattr(raw, "scores", None)
    if boxes is not None and texts is not None:
        regions: list[RawTextRegion] = []
        score_list = list(scores) if scores is not None else [1.0] * len(list(texts))
        for box, text, score in zip(list(boxes), list(texts), score_list, strict=False):
            try:
                points = [(float(p[0]), float(p[1])) for p in box]
                regions.append(RawTextRegion(text=str(text), confidence=float(score), box=points))
            except (TypeError, ValueError, IndexError):
                continue
        return regions

    payload = raw[0] if isinstance(raw, tuple) and raw else raw
    if not payload:
        return []

    regions: list[RawTextRegion] = []
    for entry in payload:
        try:
            box, text, score = entry
            points = [(float(p[0]), float(p[1])) for p in box]
            regions.append(RawTextRegion(text=str(text), confidence=float(score), box=points))
        except (TypeError, ValueError, IndexError):
            continue
    return regions
