"""
OCR normalization (Phase 12) — the adapter to the Phase 11 OCR contract.

Turns provider `RawTextRegion`s into `app.schemas.ocr.OCRResult` values and folds
them into an `OCRResponse`. This is a purely mechanical transform:

- polygon points -> ordered, clamped integer bbox [x1, y1, x2, y2]
- raw score      -> confidence clamped to [0, 1]
- region set     -> SUCCESS / LOW_CONFIDENCE / NO_TEXT_DETECTED

It does NOT interpret text. "MRP ₹50" stays the string "MRP ₹50"; it never becomes a
value, a field, or a compliance signal (spec §19, §23, §24). PROCESSING_ERROR and
INVALID_IMAGE are decided upstream (the service/pipeline), never here.
"""

import math

from app.core.enums import OCRStatus
from app.ocr.provider import RawTextRegion
from app.schemas.imaging import OCRResponse
from app.schemas.ocr import OCRResult


def to_bbox(
    points: list[tuple[float, float]],
    *,
    width: int | None = None,
    height: int | None = None,
) -> list[int]:
    """
    Convert a polygon to an axis-aligned integer bbox [x1, y1, x2, y2].

    Coordinates are floored/ceiled to fully enclose the polygon, clamped to be
    non-negative, and (when the image size is given) clamped to the image bounds.
    The result always satisfies the OCRResult invariant x2 >= x1 and y2 >= y1.
    """
    if not points:
        return [0, 0, 0, 0]

    xs = [float(p[0]) for p in points]
    ys = [float(p[1]) for p in points]

    x1 = max(0, int(math.floor(min(xs))))
    y1 = max(0, int(math.floor(min(ys))))
    x2 = max(x1, int(math.ceil(max(xs))))
    y2 = max(y1, int(math.ceil(max(ys))))

    if width is not None:
        x1 = min(x1, width)
        x2 = min(x2, width)
    if height is not None:
        y1 = min(y1, height)
        y2 = min(y2, height)

    return [x1, y1, x2, y2]


def _clamp_confidence(value: float) -> float:
    if value < 0:
        return 0.0
    if value > 1:
        return 1.0
    return float(value)


def normalize_region(
    raw: RawTextRegion,
    *,
    width: int | None = None,
    height: int | None = None,
) -> OCRResult:
    """Adapt a single raw region to the Phase 11 OCRResult contract."""
    return OCRResult(
        text=raw.text.strip(),
        confidence=_clamp_confidence(raw.confidence),
        bbox=to_bbox(raw.box, width=width, height=height),
    )


def build_ocr_response(
    raw_regions: list[RawTextRegion],
    *,
    low_confidence_threshold: float,
    provider: str | None = None,
    languages: list[str] | None = None,
    width: int | None = None,
    height: int | None = None,
    warnings: list[str] | None = None,
) -> OCRResponse:
    """
    Normalize regions and classify the read.

    Regions whose text is empty after stripping are dropped (engines occasionally
    emit blank detections). With no remaining text the status is NO_TEXT_DETECTED —
    which explicitly does NOT mean any declaration is missing (spec §20).
    """
    languages = list(languages or [])
    warnings = list(warnings or [])

    regions = [
        normalize_region(raw, width=width, height=height)
        for raw in raw_regions
        if raw.text and raw.text.strip()
    ]

    if not regions:
        return OCRResponse(
            status=OCRStatus.NO_TEXT_DETECTED,
            regions=[],
            provider=provider,
            languages=languages,
            mean_confidence=None,
            warnings=warnings,
        )

    mean_confidence = sum(r.confidence for r in regions) / len(regions)
    status = (
        OCRStatus.LOW_CONFIDENCE
        if mean_confidence <= low_confidence_threshold
        else OCRStatus.SUCCESS
    )

    return OCRResponse(
        status=status,
        regions=regions,
        provider=provider,
        languages=languages,
        mean_confidence=mean_confidence,
        warnings=warnings,
    )
