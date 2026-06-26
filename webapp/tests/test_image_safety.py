"""Tests for the upload safety pipeline (validation + EXIF strip + re-encode)."""

import io

import pytest
from PIL import Image

from common.image_safety import ImageValidationError, _sniff_mime, validate_and_sanitize


def _png(size=(16, 16)):
    buf = io.BytesIO()
    Image.new("RGB", size, (10, 20, 30)).save(buf, format="PNG")
    return buf.getvalue()


def test_valid_png_is_normalised_to_jpeg():
    out, content_type = validate_and_sanitize(_png(), "image/png")
    assert content_type == "image/jpeg"
    assert Image.open(io.BytesIO(out)).format == "JPEG"


def test_rejects_non_image_bytes():
    with pytest.raises(ImageValidationError):
        validate_and_sanitize(b"definitely not an image", "image/png")


def test_sniff_recognizes_heif_family():
    # HEIC/AVIF start with a "....ftyp<brand>" ISO-BMFF box.
    assert _sniff_mime(b"\x00\x00\x00\x18ftypheic\x00\x00\x00\x00") == "image/heic"
    assert _sniff_mime(b"\x00\x00\x00\x18ftypmif1\x00\x00\x00\x00") == "image/heic"
    assert _sniff_mime(b"\x00\x00\x00\x18ftypavif\x00\x00\x00\x00") == "image/avif"
    assert _sniff_mime(b"not an image at all") is None


def test_rejects_oversized(settings):
    settings.MAX_UPLOAD_BYTES = 10
    with pytest.raises(ImageValidationError):
        validate_and_sanitize(_png((64, 64)), "image/png")


def test_rejects_disallowed_type(settings):
    settings.ALLOWED_IMAGE_TYPES = ["image/png"]
    # A JPEG should now be rejected by the allowlist.
    buf = io.BytesIO()
    Image.new("RGB", (16, 16)).save(buf, format="JPEG")
    with pytest.raises(ImageValidationError):
        validate_and_sanitize(buf.getvalue(), "image/jpeg")
