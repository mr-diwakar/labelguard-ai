"""
Image validation (Phase 12).

Cheap, dependency-free checks on the raw upload bytes: non-empty, within the size
limit, and a supported image format detected from the file's *magic bytes* — never
from a caller-supplied filename or content-type. Decode-level checks (corruption,
dimension bounds) live in `intake.py`, which has the decoded image in hand.

Every rejection raises `AppError`, so the message is safe to return to a client and
never contains a filesystem path or raw library text.
"""

from app.core.config import Settings
from app.core.exceptions import AppError

# Magic-byte signatures. Extensions and content-type headers are untrusted.
_JPEG_PREFIX = b"\xff\xd8\xff"
_PNG_PREFIX = b"\x89PNG\r\n\x1a\n"


def detect_format(data: bytes) -> str | None:
    """Return 'JPEG' / 'PNG' / 'WEBP' from the file signature, or None."""
    if data.startswith(_JPEG_PREFIX):
        return "JPEG"
    if data.startswith(_PNG_PREFIX):
        return "PNG"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "WEBP"
    return None


def ensure_supported(data: bytes, settings: Settings) -> str:
    """
    Validate size and format of the raw bytes. Returns the detected format name.

    Raises AppError for empty, oversized, or unsupported inputs.
    """
    if not data:
        raise AppError("EMPTY_IMAGE", "The uploaded image is empty.", status_code=422)

    if len(data) > settings.scan_max_file_bytes:
        raise AppError(
            "IMAGE_TOO_LARGE",
            "The uploaded image exceeds the maximum allowed size.",
            details={"max_bytes": settings.scan_max_file_bytes, "actual_bytes": len(data)},
            status_code=413,
        )

    detected = detect_format(data)
    if detected is None or detected not in settings.scan_supported_formats:
        raise AppError(
            "UNSUPPORTED_FORMAT",
            "The uploaded file is not a supported image format.",
            details={"supported": list(settings.scan_supported_formats)},
            status_code=415,
        )

    return detected


def ensure_dimensions(width: int, height: int, settings: Settings) -> None:
    """Reject images that are too small to be usable or unreasonably large."""
    if width < 1 or height < 1:
        raise AppError("INVALID_DIMENSIONS", "The image has invalid dimensions.", status_code=422)

    if width > settings.image_max_width or height > settings.image_max_height:
        raise AppError(
            "INVALID_DIMENSIONS",
            "The image dimensions are unreasonably large.",
            details={
                "max_width": settings.image_max_width,
                "max_height": settings.image_max_height,
                "width": width,
                "height": height,
            },
            status_code=422,
        )
