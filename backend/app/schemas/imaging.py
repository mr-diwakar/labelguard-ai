"""
Phase 12 image-intake / OCR container schemas.

These aggregate the results of the scan pipeline. They REUSE the Phase 11 OCR
contract (`app.schemas.ocr.OCRResult`) for every recognised region rather than
defining a second OCR model, and `ImageQualityReport` adapts DOWN to the existing
`ImageQualityResult` so the thin Phase 11 quality contract stays the shared
interface. Nothing here carries a legal meaning (see enums docstrings).
"""

from pydantic import Field

from app.core.enums import (
    BrightnessStatus,
    ImageQualityStatus,
    OCRStatus,
    OrientationStatus,
    ResolutionStatus,
)
from app.schemas.common import APIModel
from app.schemas.ocr import ImageQualityResult, OCRResult


class BlurResult(APIModel):
    """Variance-of-Laplacian sharpness metric. Lower score = blurrier."""

    is_blurry: bool
    score: float = Field(ge=0)
    threshold: float = Field(ge=0)


class BrightnessResult(APIModel):
    """Mean grayscale brightness on a 0..255 scale."""

    status: BrightnessStatus
    mean: float = Field(ge=0, le=255)
    min_threshold: float = Field(ge=0, le=255)
    max_threshold: float = Field(ge=0, le=255)


class ResolutionResult(APIModel):
    width: int = Field(ge=1)
    height: int = Field(ge=1)
    min_width: int = Field(ge=1)
    min_height: int = Field(ge=1)
    status: ResolutionStatus


class OrientationResult(APIModel):
    """Deterministic, EXIF-only orientation state. rotation_applied is degrees."""

    status: OrientationStatus
    rotation_applied: int = 0


class ImageQualityReport(APIModel):
    """
    Full quality assessment for one scanned image.

    The purpose is to flag images where OCR is likely unreliable — NOT to prove a
    label is readable, and never to make a legal decision.
    """

    status: ImageQualityStatus
    blur: BlurResult
    brightness: BrightnessResult
    resolution: ResolutionResult
    orientation: OrientationResult
    warnings: list[str] = Field(default_factory=list)

    def to_image_quality_result(self) -> ImageQualityResult:
        """
        Adapt DOWN to the thin Phase 11 quality contract. UNUSABLE maps to
        `usable=False`; OK/WARNING are both usable (a warning does not block OCR).
        """
        usable = self.status is not ImageQualityStatus.UNUSABLE
        reason = None if usable else "; ".join(self.warnings) or "Image quality is unusable for OCR."
        return ImageQualityResult(usable=usable, reason=reason)


class OCRResponse(APIModel):
    """
    Result of the OCR stage. `regions` are Phase 11 `OCRResult` values (reused).

    `status` distinguishes an OCR failure (PROCESSING_ERROR / INVALID_IMAGE),
    an empty read (NO_TEXT_DETECTED) and a low-confidence read (LOW_CONFIDENCE)
    from SUCCESS. None of these are declaration- or compliance-level statements.
    """

    status: OCRStatus
    regions: list[OCRResult] = Field(default_factory=list)
    provider: str | None = None
    languages: list[str] = Field(default_factory=list)
    mean_confidence: float | None = Field(default=None, ge=0, le=1)
    warnings: list[str] = Field(default_factory=list)


class ScanProcessingResult(APIModel):
    """
    What the internal `process_scan` service returns.

    Both the image-quality report and the OCR result are preserved (quality
    metadata is not discarded after OCR — a later phase may need it for
    manual-review logic). This is the STOP point of Phase 12: no declaration
    extraction and no legal assessment.
    """

    scan_id: str
    image_format: str
    width: int = Field(ge=1)
    height: int = Field(ge=1)
    image_quality: ImageQualityReport
    ocr: OCRResponse
    warnings: list[str] = Field(default_factory=list)
