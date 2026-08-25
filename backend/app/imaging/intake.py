"""
Scan intake (Phase 12).

Turns a raw upload (`bytes` + optional filename/content-type) into a decoded,
upright `PreparedImage` ready for quality checks and OCR. The image is decoded
exactly once here; every later stage works on copies of `PreparedImage.bgr`.

Design notes:
- The original `bytes` are never mutated (they are immutable) and never written to
  disk, so the original scan is preserved for the life of the request (spec §15).
- Orientation is read from EXIF only — no ML, no heuristic rotation. If EXIF cannot
  be read the orientation is reported UNKNOWN (a warning), never guessed.
- Decode failures become an `AppError` with a client-safe message; the underlying
  Pillow/OpenCV exception text is never surfaced.
"""

from dataclasses import dataclass
from io import BytesIO
from uuid import uuid4

import cv2
import numpy as np
from PIL import Image, ImageOps

from app.core.config import Settings, get_settings
from app.core.enums import OrientationStatus
from app.core.exceptions import AppError
from app.imaging.validation import ensure_dimensions, ensure_supported
from app.schemas.imaging import OrientationResult

# EXIF orientation tag id and the rotation (degrees) each value corresponds to.
# Only the rotation component is reported as metadata; mirror-only values still
# report CORRECTED but 0 degrees. Values are informational, not legal.
_EXIF_ORIENTATION_TAG = 274
_EXIF_ORIENTATION_ROTATION = {1: 0, 2: 0, 3: 180, 4: 180, 5: 90, 6: 90, 7: 270, 8: 270}


@dataclass(frozen=True)
class PreparedImage:
    """A decoded, EXIF-upright image plus intake metadata. Not a wire schema."""

    scan_id: str
    image_format: str
    bgr: np.ndarray  # HxWx3, BGR channel order (OpenCV convention)
    width: int
    height: int
    orientation: OrientationResult


def _read_orientation(pil_img: Image.Image) -> OrientationResult:
    """Read the EXIF orientation tag. Never raises; UNKNOWN on any failure."""
    try:
        exif = pil_img.getexif()
    except Exception:
        return OrientationResult(status=OrientationStatus.UNKNOWN, rotation_applied=0)

    tag = exif.get(_EXIF_ORIENTATION_TAG) if exif else None
    if not tag or int(tag) == 1:
        return OrientationResult(status=OrientationStatus.OK, rotation_applied=0)

    rotation = _EXIF_ORIENTATION_ROTATION.get(int(tag), 0)
    return OrientationResult(status=OrientationStatus.CORRECTED, rotation_applied=rotation)


def load_scan(
    data: bytes,
    *,
    filename: str | None = None,
    content_type: str | None = None,
    settings: Settings | None = None,
) -> PreparedImage:
    """
    Validate and decode an uploaded image into a `PreparedImage`.

    `filename` / `content_type` are accepted for logging/telemetry only — the
    format is always determined from the magic bytes, never from these hints.
    """
    settings = settings or get_settings()

    # Byte-level validation first (empty / oversized / unsupported) — cheap and
    # avoids decoding anything we already know we will reject.
    image_format = ensure_supported(data, settings)

    try:
        with Image.open(BytesIO(data)) as pil_img:
            pil_img.load()  # force a full decode so truncated files fail here
            orientation = _read_orientation(pil_img)
            upright = ImageOps.exif_transpose(pil_img)  # new image; applies EXIF
            rgb = np.asarray(upright.convert("RGB"))
    except AppError:
        raise
    except Exception as exc:  # corrupt, truncated, or otherwise undecodable
        raise AppError(
            "CORRUPTED_IMAGE",
            "The uploaded image could not be decoded.",
            status_code=422,
        ) from exc

    # OpenCV works in BGR; convert once so the whole pipeline shares one convention.
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    height, width = bgr.shape[:2]

    # Hard sanity bounds (0-size / decompression-bomb). The *minimum* usable size
    # is a quality signal (ResolutionStatus.TOO_SMALL), decided later, not here.
    ensure_dimensions(width, height, settings)

    return PreparedImage(
        scan_id=uuid4().hex,
        image_format=image_format,
        bgr=bgr,
        width=width,
        height=height,
        orientation=orientation,
    )
