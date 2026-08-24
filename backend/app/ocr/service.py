"""
OCR service (Phase 12).

Thin orchestration around an injectable `OCRProvider`: run the provider, then hand
its raw regions to `build_ocr_response` for normalization + classification. Any
exception from the provider (missing engine, model download failure, decode error
inside the engine) is converted to an OCRStatus.PROCESSING_ERROR response with a
client-safe warning — an OCR failure is an operational fault, never a legal verdict
(spec §20). The engine's raw exception text is logged, not surfaced.
"""

from app.core.config import Settings, get_settings
from app.core.enums import OCRStatus
from app.core.logging_config import get_logger
from app.ocr.normalization import build_ocr_response
from app.ocr.provider import OCRProvider, RawTextRegion
from app.schemas.imaging import OCRResponse

logger = get_logger(__name__)


class OCRService:
    """Runs a single OCRProvider and returns a normalized OCRResponse."""

    def __init__(self, provider: OCRProvider, *, settings: Settings | None = None) -> None:
        self._provider = provider
        self._settings = settings or get_settings()

    def run(
        self,
        image,
        *,
        width: int | None = None,
        height: int | None = None,
        languages: list[str] | None = None,
        scale_x: float = 1.0,
        scale_y: float = 1.0,
    ) -> OCRResponse:
        """
        Run OCR and normalize. `scale_x`/`scale_y` map bbox coordinates from the
        (possibly resized) image handed to the provider back to the original image
        space, so bboxes stay consistent with the reported width/height.
        """
        languages = list(languages or self._settings.ocr_languages)
        provider_name = getattr(self._provider, "name", None)

        try:
            raw_regions = self._provider.recognize(image)
        except Exception:
            # Log the detail server-side; return a safe, generic response.
            logger.exception("OCR provider %s failed", provider_name)
            return OCRResponse(
                status=OCRStatus.PROCESSING_ERROR,
                regions=[],
                provider=provider_name,
                languages=languages,
                mean_confidence=None,
                warnings=["OCR could not be completed for this image."],
            )

        if scale_x != 1.0 or scale_y != 1.0:
            raw_regions = [_rescale_region(r, scale_x, scale_y) for r in raw_regions]

        return build_ocr_response(
            raw_regions,
            low_confidence_threshold=self._settings.ocr_low_confidence_threshold,
            provider=provider_name,
            languages=languages,
            width=width,
            height=height,
        )


def _rescale_region(region: RawTextRegion, scale_x: float, scale_y: float) -> RawTextRegion:
    """Map a region's polygon from resized-image space back to original space."""
    box = [(x / scale_x, y / scale_y) for (x, y) in region.box]
    return RawTextRegion(text=region.text, confidence=region.confidence, box=box)
