"""
Extraction-layer contracts (Phase 15).

These models are RICHER than the stable Phase 11 ``ExtractedDeclaration`` contract:
they preserve every candidate value the extractor considered (the spec forbids
arbitrarily picking one when the evidence is ambiguous) together with the OCR
evidence and a *separate* extraction confidence. They then adapt DOWN to
``ExtractedDeclaration`` -- the single shape handed to the legal engine -- mirroring
the codebase's established rich-model -> stable-contract pattern
(``ImageQualityReport`` -> ``ImageQualityResult``, ``RawTextRegion`` -> ``OCRResult``).

Layer discipline:
    * OCR confidence, extraction confidence and legal assessment are kept SEPARATE.
    * No legal interpretation happens here. This module imports schemas + enums only;
      it never imports the compliance package, so extraction can be replaced without
      touching Legal Metrology logic.
"""

from __future__ import annotations

from pydantic import Field

from app.core.enums import DeclarationSource, DetectionStatus
from app.schemas.common import APIModel
from app.schemas.contracts.detection import ExtractedDeclaration


class DeclarationCandidate(APIModel):
    """One possible reading for a field, with the evidence and confidence behind it.

    ``extraction_confidence`` is the extraction layer's own confidence, distinct
    from ``ocr_confidence`` (how sure OCR was of the characters). ``raw_text`` keeps
    the OCR text the candidate came from so a reviewer can see what was actually read
    (e.g. the ambiguous ``"5O"`` behind a corrected ``"50"``).
    """

    value: str | None = None
    unit: str | None = None
    extraction_confidence: float = Field(ge=0, le=1)
    ocr_confidence: float | None = Field(default=None, ge=0, le=1)
    source_reference: str | None = None
    bbox: list[int] | None = Field(default=None, min_length=4, max_length=4)
    raw_text: str | None = None
    note: str | None = None


class FieldExtraction(APIModel):
    """The extraction layer's full conclusion about one declaration field.

    ``candidates`` preserves ALL plausible readings; ``status`` is the honest
    extraction-layer :class:`DetectionStatus`. ``to_extracted_declaration`` adapts
    DOWN to the Phase 11 contract, carrying the best candidate's value but keeping
    the status intact (an UNCERTAIN field stays UNCERTAIN, so the engine routes it to
    manual review rather than silently trusting a guessed value).
    """

    field: str
    status: DetectionStatus
    candidates: list[DeclarationCandidate] = Field(default_factory=list)
    source: DeclarationSource = DeclarationSource.OCR

    @property
    def best(self) -> DeclarationCandidate | None:
        """Highest-confidence candidate, or None when the field has no candidates."""
        if not self.candidates:
            return None
        return max(self.candidates, key=lambda candidate: candidate.extraction_confidence)

    @property
    def is_ambiguous(self) -> bool:
        """True when more than one distinct (value, unit) reading was found."""
        distinct = {(candidate.value, candidate.unit) for candidate in self.candidates}
        return len(distinct) > 1

    def to_extracted_declaration(self) -> ExtractedDeclaration:
        """Adapt to the Phase 11 ``ExtractedDeclaration`` handed to the legal engine."""
        best = self.best
        return ExtractedDeclaration(
            field=self.field,
            value=best.value if best else None,
            unit=best.unit if best else None,
            confidence=best.extraction_confidence if best else None,
            status=self.status,
            source=self.source,
            source_reference=best.source_reference if best else None,
            bbox=best.bbox if best else None,
        )


class ExtractionResult(APIModel):
    """Everything the extraction layer produced for one scan.

    ``fields`` are only the declarations for which candidates were found. A field's
    absence here means "not detected in this scan", which is NOT the same as
    "declaration is absent from the product" -- the orchestrator/engine decides that
    separately, conservatively, from the inspection context.
    """

    fields: list[FieldExtraction] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    def to_extracted_declarations(self) -> list[ExtractedDeclaration]:
        """Adapt every field DOWN to the Phase 11 contract, in a stable order."""
        return [field.to_extracted_declaration() for field in self.fields]
