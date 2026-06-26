"""Image upload validation + sanitisation.

Implements safety rules #1 (validate real content, not extension) and #2 (strip
EXIF/GPS metadata and re-encode). See docs/safety.md.

Supports JPEG/PNG/WebP and — when ``pillow-heif`` is installed — HEIC/HEIF/AVIF
(the formats modern phones save in). Everything is normalised to clean JPEG.
"""

from __future__ import annotations

import io

from django.conf import settings
from PIL import Image

# Register the HEIF/HEIC/AVIF opener if available (optional dependency). Phones
# commonly save HEIC; without this Pillow can't decode it and uploads fail.
try:  # pragma: no cover - depends on optional system wheel
    from pillow_heif import register_heif_opener

    register_heif_opener()
    _HEIF_OK = True
except Exception:  # noqa: BLE001
    _HEIF_OK = False

# ISO-BMFF brands that indicate a HEIF-family image (HEIC/AVIF).
_HEIF_BRANDS = {
    b"heic",
    b"heix",
    b"heis",
    b"hevc",
    b"hevx",
    b"mif1",
    b"msf1",
    b"heif",
    b"avif",
    b"avis",
}


class ImageValidationError(Exception):
    """Raised when an upload fails a safety check; mapped to HTTP 400."""


def _sniff_mime(head: bytes) -> str | None:
    """Identify the image type from its magic bytes (content, not extension)."""
    if head[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if head[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"
    # HEIF family: "....ftyp<brand>" box at the start.
    if head[4:8] == b"ftyp" and head[8:12] in _HEIF_BRANDS:
        return "image/avif" if head[8:12] in (b"avif", b"avis") else "image/heic"
    return None


def validate_and_sanitize(raw: bytes, declared_content_type: str = "") -> tuple[bytes, str]:
    """Validate an uploaded image and return sanitised ``(bytes, content_type)``.

    Steps:
      1. Size limit (rule #1).
      2. Magic-byte sniff against the allowlist (rule #1) — ignores the client
         supplied extension/Content-Type which can lie.
      3. ``Image.verify()`` to reject corrupt/decompression-bomb files.
      4. Re-decode and re-encode, dropping all EXIF/metadata (rule #2).
    """
    if not raw:
        raise ImageValidationError("Empty file.")
    if len(raw) > settings.MAX_UPLOAD_BYTES:
        raise ImageValidationError(
            f"File too large (max {settings.MAX_UPLOAD_BYTES // (1024 * 1024)} MiB)."
        )

    sniffed = _sniff_mime(raw[:16])
    if sniffed is None or sniffed not in settings.ALLOWED_IMAGE_TYPES:
        hint = ""
        if sniffed in ("image/heic", "image/avif") and not _HEIF_OK:
            hint = " (HEIC/AVIF support is unavailable on the server)"
        raise ImageValidationError(
            "Unsupported image type. Allowed: " + ", ".join(settings.ALLOWED_IMAGE_TYPES) + hint
        )

    # Verify integrity on a throwaway copy (verify() leaves the image unusable).
    try:
        Image.open(io.BytesIO(raw)).verify()
    except Exception as exc:  # noqa: BLE001
        raise ImageValidationError("File is not a valid image.") from exc

    # Re-open, normalise mode, strip metadata by re-encoding without exif/icc.
    try:
        img = Image.open(io.BytesIO(raw))
        img = img.convert("RGB")
    except Exception as exc:  # noqa: BLE001
        raise ImageValidationError("Could not decode image.") from exc

    out = io.BytesIO()
    # Normalise everything to JPEG: smallest, no alpha, metadata-free.
    img.save(out, format="JPEG", quality=90, optimize=True)
    return out.getvalue(), "image/jpeg"
