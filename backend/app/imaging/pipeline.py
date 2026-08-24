"""
Scan processing pipeline (Phase 12) — the internal `process_scan` service.

    intake -> image quality -> preprocessing -> OCR -> ScanProcessingResult

This is the clean internal service the spec asks for (§26): a function, not a public
`/scan` API. It never decides compliance, never extracts declarations, and always
preserves BOTH the image-quality report and the OCR result (§22, §23).

Failure model:
- Hard intake faults (empty / unsupported / corrupt / bad dimensions) raise AppError
  from `load_scan`; there is no decoded image to build a result around, so the caller
  (a future API layer) turns the AppError into a JSON error envelope.
- Quality is advisory: even an UNUSABLE image still goes through OCR, because quality
  and OCR are independent signals (§22). The quality warnings tell the caller why a
  read may be poor.
- If no OCR provider is available, OCR is reported PROCESSING_ERROR (not a crash, and
  not a legal statement). A degenerate OCR input is reported INVALID_IMAGE.
"""

from app.core.config import Settings, get_settings
from app.core.enums import OCRStatus
from app.imaging.intake import load_scan
from app.imaging.preprocessing import ImagePreprocessor
from app.imaging.quality import assess_quality
from app.ocr.paddle_adapter import PaddleOCRProvider
from app.ocr.provider import OCRProvider
from app.ocr.service import OCRService
from app.schemas.imaging import OCRResponse, ScanProcessingResult


def _resolve_provider(
    provider: OCRProvider | None,
    settings: Settings,
) -> OCRProvider | None:
    """Explicit provider wins; otherwise use PaddleOCR only if it is installed."""
    if provider is not None:
        return provider
    if PaddleOCRProvider.available():
        return PaddleOCRProvider(settings=settings)
    return None


def _run_ocr(
    ocr_image,
    *,
    original_width: int,
    original_height: int,
    provider: OCRProvider | None,
    settings: Settings,
) -> OCRResponse:
    resolved = _resolve_provider(provider, settings)
    if resolved is None:
        return OCRResponse(
            status=OCRStatus.PROCESSING_ERROR,
            provider=None,
            languages=list(settings.ocr_languages),
            warnings=["No OCR provider is available; text was not extracted."],
        )

    if ocr_image is None or getattr(ocr_image, "size", 0) == 0:
        return OCRResponse(
            status=OCRStatus.INVALID_IMAGE,
            provider=getattr(resolved, "name", None),
            languages=list(settings.ocr_languages),
            warnings=["The image could not be prepared for OCR."],
        )

    # Map OCR-space bboxes back to the original image coordinate space.
    ocr_height, ocr_width = ocr_image.shape[:2]
    scale_x = ocr_width / float(original_width) if original_width else 1.0
    scale_y = ocr_height / float(original_height) if original_height else 1.0

    service = OCRService(resolved, settings=settings)
    return service.run(
        ocr_image,
        width=original_width,
        height=original_height,
        languages=list(settings.ocr_languages),
        scale_x=scale_x,
        scale_y=scale_y,
    )


def process_scan(
    image_bytes: bytes,
    *,
    filename: str | None = None,
    content_type: str | None = None,
    provider: OCRProvider | None = None,
    settings: Settings | None = None,
) -> ScanProcessingResult:
    """
    Process one scanned image end-to-end (intake -> quality -> OCR).

    Raises AppError for inputs that cannot be decoded at all. Otherwise always
    returns a ScanProcessingResult carrying the quality report and OCR output.
    """
    settings = settings or get_settings()

    prepared = load_scan(
        image_bytes, filename=filename, content_type=content_type, settings=settings
    )

    quality = assess_quality(prepared, settings)

    preprocessor = ImagePreprocessor(settings)
    ocr_image = preprocessor.prepare_for_ocr(prepared.bgr)

    ocr = _run_ocr(
        ocr_image,
        original_width=prepared.width,
        original_height=prepared.height,
        provider=provider,
        settings=settings,
    )

    # Surface the quality warnings at the top level too, for convenience. OCR
    # warnings stay on the OCR object so the two signals are not conflated.
    warnings = list(quality.warnings)

    return ScanProcessingResult(
        scan_id=prepared.scan_id,
        image_format=prepared.image_format,
        width=prepared.width,
        height=prepared.height,
        image_quality=quality,
        ocr=ocr,
        warnings=warnings,
    )
