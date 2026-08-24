"""
Image quality assessment (Phase 12).

Computes three independent, well-known metrics on the decoded image and folds them,
together with the intake orientation, into an `ImageQualityReport`:

- blur       : variance of the Laplacian (sharp images have high edge variance)
- brightness : mean of the grayscale image on a 0..255 scale
- resolution : decoded width/height against the configured minimum

The overall status is a transparent, tunable heuristic whose ONLY job is to flag
images where OCR is likely unreliable. It is never a legal/compliance judgement, and
a poor quality score never means "a declaration is missing" (spec §20, §23).
"""

import cv2

from app.core.config import Settings, get_settings
from app.core.enums import (
    BrightnessStatus,
    ImageQualityStatus,
    OrientationStatus,
    ResolutionStatus,
)
from app.imaging.intake import PreparedImage
from app.schemas.imaging import (
    BlurResult,
    BrightnessResult,
    ImageQualityReport,
    ResolutionResult,
)

# Below half the blur threshold, edges are so smeared that characters are
# effectively unrecoverable — a single-signal reason to call the image unusable.
_SEVERE_BLUR_FRACTION = 0.5


def _measure_blur(gray, threshold: float) -> BlurResult:
    score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    return BlurResult(is_blurry=score < threshold, score=score, threshold=threshold)


def _measure_brightness(gray, settings: Settings) -> BrightnessResult:
    mean = float(gray.mean())
    if mean < settings.image_brightness_min:
        status = BrightnessStatus.TOO_DARK
    elif mean > settings.image_brightness_max:
        status = BrightnessStatus.TOO_BRIGHT
    else:
        status = BrightnessStatus.ACCEPTABLE
    return BrightnessResult(
        status=status,
        mean=mean,
        min_threshold=settings.image_brightness_min,
        max_threshold=settings.image_brightness_max,
    )


def _measure_resolution(prepared: PreparedImage, settings: Settings) -> ResolutionResult:
    too_small = prepared.width < settings.image_min_width or prepared.height < settings.image_min_height
    return ResolutionResult(
        width=prepared.width,
        height=prepared.height,
        min_width=settings.image_min_width,
        min_height=settings.image_min_height,
        status=ResolutionStatus.TOO_SMALL if too_small else ResolutionStatus.OK,
    )


def classify_quality(
    blur: BlurResult,
    brightness: BrightnessResult,
    resolution: ResolutionResult,
    orientation: OrientationResult,
    *,
    settings: Settings,
) -> tuple[ImageQualityStatus, list[str]]:
    """
    Fold the individual metrics into an overall status + human-readable warnings.

    Transparent, tunable heuristic (never a legal decision):
    - UNUSABLE if the blur is severe (edges effectively gone), or two or more
      independent quality problems compound.
    - WARNING if any single problem or a non-blocking caveat (unknown orientation)
      is present.
    - OK otherwise.

    Orientation is advisory only and never forces UNUSABLE — it does not stop OCR.
    """
    warnings: list[str] = []
    if blur.is_blurry:
        warnings.append("Image appears blurry; OCR may be unreliable.")
    if brightness.status is BrightnessStatus.TOO_DARK:
        warnings.append("Image is darker than recommended; OCR may be unreliable.")
    elif brightness.status is BrightnessStatus.TOO_BRIGHT:
        warnings.append("Image is brighter than recommended; OCR may be unreliable.")
    if resolution.status is ResolutionStatus.TOO_SMALL:
        warnings.append("Image resolution is below the recommended minimum for reliable OCR.")
    if orientation.status is OrientationStatus.UNKNOWN:
        warnings.append("Image orientation could not be determined from metadata.")

    # Independent quality problems (orientation excluded — it never blocks OCR).
    problems = sum(
        (
            blur.is_blurry,
            brightness.status is not BrightnessStatus.ACCEPTABLE,
            resolution.status is ResolutionStatus.TOO_SMALL,
        )
    )
    severe_blur = blur.score < blur.threshold * _SEVERE_BLUR_FRACTION

    if severe_blur or problems >= 2:
        status = ImageQualityStatus.UNUSABLE
    elif problems >= 1 or warnings:
        status = ImageQualityStatus.WARNING
    else:
        status = ImageQualityStatus.OK

    return status, warnings


def assess_quality(
    prepared: PreparedImage,
    settings: Settings | None = None,
) -> ImageQualityReport:
    """Build the full quality report for an already-decoded image."""
    settings = settings or get_settings()
    gray = cv2.cvtColor(prepared.bgr, cv2.COLOR_BGR2GRAY)

    blur = _measure_blur(gray, settings.image_blur_threshold)
    brightness = _measure_brightness(gray, settings)
    resolution = _measure_resolution(prepared, settings)
    orientation = prepared.orientation

    status, warnings = classify_quality(
        blur, brightness, resolution, orientation, settings=settings
    )

    return ImageQualityReport(
        status=status,
        blur=blur,
        brightness=brightness,
        resolution=resolution,
        orientation=orientation,
        warnings=warnings,
    )
