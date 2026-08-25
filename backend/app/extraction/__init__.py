"""
Declaration extraction (Phase 15).

Converts OCR regions into structured declarations for the Legal Metrology engine.
This is a distinct layer from OCR: OCR recognises characters; extraction decides
what declaration a region represents, with its own confidence and explicit
uncertainty. Deterministic only -- no LLM, no external services, no legal judgement.

Public API:
    * ``DeclarationExtractor`` / ``extract_declarations`` -- the service entry point.
    * ``ExtractionResult`` / ``FieldExtraction`` / ``DeclarationCandidate`` -- the
      rich, candidate-preserving contracts (adapt DOWN to ``ExtractedDeclaration``).
"""

from app.extraction.service import DeclarationExtractor, extract_declarations
from app.schemas.extraction import DeclarationCandidate, ExtractionResult, FieldExtraction

__all__ = [
    "DeclarationExtractor",
    "extract_declarations",
    "ExtractionResult",
    "FieldExtraction",
    "DeclarationCandidate",
]
