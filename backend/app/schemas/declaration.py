"""Structured declaration extracted from OCR. The legal engine consumes this, not raw text."""

from pydantic import Field

from app.core.enums import DeclarationSource, DeclarationStatus
from app.schemas.common import APIModel, BoundingBox, MobileModel


class Declaration(APIModel):
    """
    Integration contract between extraction and the legal engine.

    Example:
        {
            "field": "mrp",
            "value": "50",
            "confidence": 0.98,
            "source": "OCR",
            "bbox": [100, 200, 300, 250],
            "status": "DETECTED"
        }
    """

    field: str
    value: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    source: DeclarationSource = DeclarationSource.OCR
    bbox: list[int] | None = Field(default=None, min_length=4, max_length=4)
    status: DeclarationStatus


class DeclarationCheck(MobileModel):
    """One line in a mobile inspection assessment."""

    declaration_key: str = Field(alias="declarationKey")
    note: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    bounding_box: BoundingBox | None = Field(default=None, alias="boundingBox")
