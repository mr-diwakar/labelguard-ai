"""
Phase 12 OCR package: the provider abstraction, the lazy PaddleOCR adapter, the
service wrapper, and normalization to the Phase 11 `OCRResult` contract.

Note: importing this package does NOT import paddleocr (that import is lazy, inside
PaddleOCRProvider), so the package stays importable without the heavy dependency.
"""

from app.ocr.normalization import build_ocr_response, normalize_region, to_bbox
from app.ocr.provider import OCRProvider, RawTextRegion
from app.ocr.service import OCRService

__all__ = [
    "OCRProvider",
    "RawTextRegion",
    "OCRService",
    "build_ocr_response",
    "normalize_region",
    "to_bbox",
]
