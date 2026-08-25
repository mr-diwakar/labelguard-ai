"""
Evidence reference contract (Phase 11).

A generic pointer to supporting evidence (an OCR region, a product image, a
measurement, a note...). It references evidence; it does not generate or store images
and creates no file-storage infrastructure. Complements the existing EvidenceItem
(which tracks generated-artefact status for the mobile overlay).
"""

from datetime import datetime

from pydantic import Field, field_validator

from app.core.enums import EvidenceType
from app.schemas.common import APIModel


class EvidenceReference(APIModel):
    """
    Example:
        {
            "evidence_id": "ocr_region_17",
            "evidence_type": "OCR_REGION",
            "source": "paddleocr",
            "image_reference": "product_image_1",
            "bbox": [100, 200, 350, 240],
            "confidence": 0.98,
            "note": "MRP region"
        }
    """

    evidence_id: str
    evidence_type: EvidenceType
    source: str | None = None
    image_reference: str | None = None
    # Pixel box [x1, y1, x2, y2], consistent with OCRResult. Normalised overlay boxes
    # live on BoundingBox / EvidenceItem for mobile; the pixel->normalised adapter is
    # a later phase.
    bbox: list[int] | None = Field(default=None, min_length=4, max_length=4)
    timestamp: datetime | None = None
    note: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)

    @field_validator("bbox")
    @classmethod
    def _bbox_is_ordered(cls, value: list[int] | None) -> list[int] | None:
        if value is None:
            return value
        x1, y1, x2, y2 = value
        if x2 < x1 or y2 < y1:
            raise ValueError("bbox must be [x1, y1, x2, y2] with x2 >= x1 and y2 >= y1.")
        return value
