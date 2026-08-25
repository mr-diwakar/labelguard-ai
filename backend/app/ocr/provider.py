"""
OCR provider abstraction (Phase 12).

`RawTextRegion` is the provider-neutral hand-off: whatever OCR engine is used
returns a list of these, and `app.ocr.normalization` adapts them to the Phase 11
`OCRResult` contract. Keeping this layer separate is what lets PaddleOCR be swapped
for a mock in tests, or for another engine later, without touching the pipeline.

Architecture (spec §6):  engine -> OCRProvider -> RawTextRegion -> OCRResult
"""

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

import numpy as np


@dataclass(frozen=True)
class RawTextRegion:
    """
    One recognised text region, exactly as an engine reported it.

    `box` is a polygon of (x, y) pixel points (PaddleOCR returns four corners);
    it is NOT yet an ordered [x1, y1, x2, y2] bbox and may contain floats. The
    normalization step is responsible for turning it into a valid `OCRResult`.
    `confidence` is a raw engine score; normalization clamps it to [0, 1].
    """

    text: str
    confidence: float
    box: list[tuple[float, float]] = field(default_factory=list)


@runtime_checkable
class OCRProvider(Protocol):
    """Anything that can turn an image array into raw text regions."""

    @property
    def name(self) -> str:
        """Short provider identifier recorded on the OCR response (e.g. 'paddleocr:en')."""
        ...

    def recognize(self, image: np.ndarray) -> list[RawTextRegion]:
        """Run OCR on a BGR image array. May raise; callers handle failures."""
        ...
