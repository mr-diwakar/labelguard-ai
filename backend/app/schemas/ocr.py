"""Teammate 1 contract: OCRService output."""

from pydantic import Field, field_validator

from app.schemas.common import APIModel


class OCRResult(APIModel):
    """
    One recognised text region.

    Example:
        {"text": "MRP ₹50", "confidence": 0.98, "bbox": [100, 200, 300, 250]}
    """

    text: str
    confidence: float = Field(ge=0, le=1)
    bbox: list[int] = Field(min_length=4, max_length=4)

    @field_validator("bbox")
    @classmethod
    def _bbox_is_ordered(cls, value: list[int]) -> list[int]:
        x1, y1, x2, y2 = value
        if x2 < x1 or y2 < y1:
            raise ValueError("bbox must be [x1, y1, x2, y2] with x2 >= x1 and y2 >= y1.")
        return value


class ImageQualityResult(APIModel):
    usable: bool
    reason: str | None = None
