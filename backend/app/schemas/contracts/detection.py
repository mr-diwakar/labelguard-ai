"""
Extraction-layer declaration contract (Phase 11).

The future OCR/extraction pipeline produces ExtractedDeclaration objects using the
richer DetectionStatus vocabulary. The adapter below maps them DOWN to the legal
engine's Declaration/DeclarationStatus so the ComplianceEngine, its validators and
the declarations DB CHECK constraint stay unchanged.

Dependency direction: this module imports schemas + enums only. It never imports the
compliance package, so OCR can be replaced without touching Legal Metrology logic.
"""

from pydantic import Field, field_validator

from app.core.enums import DeclarationSource, DeclarationStatus, DetectionStatus
from app.schemas.common import APIModel
from app.schemas.declaration import Declaration

# The engine treats a NOT_DETECTED field as a reliable absence only when the label
# was readable and extraction confidence is not in its uncertain band (>= 0.6 in
# validators/support.py). CONFIRMED_ABSENT is an explicit assertion of absence, so
# we hand the engine a confidence at/above that band. Kept as a local constant to
# avoid importing engine internals into the contract layer.
CONFIRMED_ABSENT_CONFIDENCE = 0.95


def detection_to_declaration_status(status: DetectionStatus) -> DeclarationStatus | None:
    """
    Map an extraction-layer status to the legal engine's vocabulary.

    Returns None for NOT_APPLICABLE: applicability is decided per-rule by the
    resolver, so a not-applicable field is not fed to the engine as a declaration.
    """
    return {
        DetectionStatus.DETECTED: DeclarationStatus.DETECTED,
        DetectionStatus.UNCERTAIN: DeclarationStatus.LOW_CONFIDENCE,
        DetectionStatus.NOT_DETECTED: DeclarationStatus.NOT_DETECTED,
        DetectionStatus.CONFIRMED_ABSENT: DeclarationStatus.NOT_DETECTED,
        DetectionStatus.NOT_APPLICABLE: None,
    }[status]


class ExtractedDeclaration(APIModel):
    """
    One field the extraction layer produced from a scan.

    Example:
        {
            "field": "mrp",
            "value": "50",
            "unit": "INR",
            "confidence": 0.98,
            "status": "DETECTED",
            "source_reference": "ocr_region_17"
        }
    """

    field: str
    value: str | None = None
    unit: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    status: DetectionStatus
    source: DeclarationSource = DeclarationSource.OCR
    source_reference: str | None = None
    bbox: list[int] | None = Field(default=None, min_length=4, max_length=4)

    @field_validator("bbox")
    @classmethod
    def _bbox_is_ordered(cls, value: list[int] | None) -> list[int] | None:
        if value is None:
            return value
        x1, y1, x2, y2 = value
        if x2 < x1 or y2 < y1:
            raise ValueError("bbox must be [x1, y1, x2, y2] with x2 >= x1 and y2 >= y1.")
        return value

    def to_declaration(self, *, label_readable: bool | None = None) -> Declaration | None:
        """
        Adapt to the legal engine input.

        Returns None for NOT_APPLICABLE (the field is not evidence for the engine).
        CONFIRMED_ABSENT is handed to the engine as NOT_DETECTED with high confidence
        so its existing reliable-absence logic applies; this requires the caller to
        also mark the inspection context label_readable=True. If it does not, the
        engine safely falls back to MANUAL_REVIEW — never a silent COMPLIANT.

        label_readable is accepted for symmetry/documentation; the engine reads it
        from the ValidationContext, so it is not stored on the Declaration here.
        """
        legal_status = detection_to_declaration_status(self.status)
        if legal_status is None:
            return None

        confidence = self.confidence
        if self.status is DetectionStatus.CONFIRMED_ABSENT:
            confidence = max(self.confidence or 0.0, CONFIRMED_ABSENT_CONFIDENCE)

        return Declaration(
            field=self.field,
            value=self.value,
            confidence=confidence,
            source=self.source,
            bbox=self.bbox,
            status=legal_status,
        )
