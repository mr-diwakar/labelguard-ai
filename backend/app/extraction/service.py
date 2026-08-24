"""
Declaration extraction service (Phase 15).

Public entry point for turning OCR regions into structured declarations. It sits
strictly ABOVE OCR and strictly BELOW the legal engine: it consumes the Phase 11
``OCRResult`` contract and produces the Phase 11 ``ExtractedDeclaration`` contract
(via the richer :class:`ExtractionResult`). It performs no OCR and makes no legal
judgement.

    OCRResult[]  ->  normalise  ->  per-field extractors  ->  ExtractionResult
                                                              (candidates preserved)
                          ExtractionResult.to_extracted_declarations()  ->  engine
"""

from __future__ import annotations

from collections.abc import Sequence

from app.extraction.extractors import OcrRegion, run_extractors
from app.extraction.normalization import normalize_text
from app.schemas.extraction import ExtractionResult
from app.schemas.ocr import OCRResult


def _to_region(index: int, region: OCRResult) -> OcrRegion:
    return OcrRegion(
        index=index,
        text=normalize_text(region.text),
        confidence=region.confidence,
        bbox=list(region.bbox) if region.bbox is not None else None,
    )


class DeclarationExtractor:
    """Extracts structured declarations from OCR regions, deterministically.

    Stateless and dependency-free; a single instance can be reused. ``extract`` is a
    pure function of its input -- the same OCR regions always produce the same
    ``ExtractionResult``.
    """

    def extract(self, regions: Sequence[OCRResult]) -> ExtractionResult:
        ocr_regions = [
            _to_region(index, region)
            for index, region in enumerate(regions)
            if region.text and region.text.strip()
        ]
        if not ocr_regions:
            return ExtractionResult(
                fields=[],
                warnings=["No usable OCR text was available for declaration extraction."],
            )
        fields = run_extractors(ocr_regions)
        return ExtractionResult(fields=fields, warnings=[])


def extract_declarations(regions: Sequence[OCRResult]) -> ExtractionResult:
    """Convenience wrapper around :class:`DeclarationExtractor` for simple call sites."""
    return DeclarationExtractor().extract(regions)
