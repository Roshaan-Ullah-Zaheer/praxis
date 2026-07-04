"""OCR for scanned / image-based pages.

Tesseract is used when available. If the binary is missing (e.g. a dev machine
without it installed), OCR degrades gracefully to an empty string rather than
crashing ingestion — the page is simply indexed with whatever text exists.
"""

from __future__ import annotations

import io
import logging

logger = logging.getLogger(__name__)

_OCR_WARNED = False


def ocr_image_bytes(png_bytes: bytes) -> str:
    """Run OCR on a PNG image; returns '' if Tesseract is unavailable."""
    global _OCR_WARNED
    try:
        import pytesseract
        from PIL import Image

        img = Image.open(io.BytesIO(png_bytes))
        return pytesseract.image_to_string(img).strip()
    except Exception as exc:  # noqa: BLE001 - missing binary or decode error
        if not _OCR_WARNED:
            logger.warning("OCR unavailable (%s); scanned pages will index without OCR text.", exc)
            _OCR_WARNED = True
        return ""
