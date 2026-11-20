"""File inspector: structural facts about an uploaded file (DOC-02, DOC-04).

PDF objects and image headers are read, never rendered or executed. A damaged file gives
facts with `is_readable=False` instead of an exception.
"""

import re
import warnings
from decimal import Decimal
from pathlib import Path

import pymupdf
from PIL import Image

from app.domain.rules.upload_validation import FileFacts, FileKind, detect_kind

# Reported for an image Pillow refuses as a decompression bomb: far above any sane limit.
BOMB_MEGAPIXELS = Decimal(1000)
# 300 dpi (the OCR resolution, `ocr.render.DEFAULT_DPI`) over 72 points per inch, squared.
_PIXELS_PER_POINT_SQ = (Decimal(300) / Decimal(72)) ** 2
_SIGNATURE_BYTES = 16
_JPEG_DRAFT_DIVISOR = 8
_ACTIVE_OBJECT = re.compile(r"/JavaScript\b|/JS\b|/Launch\b|/EmbeddedFile\b|/EmbeddedFiles\b")

_FORMAT_BY_KIND = {FileKind.JPEG: "JPEG", FileKind.PNG: "PNG"}


class PillowFileInspector:
    """Implements the `FileInspector` port with PyMuPDF (PDF) and Pillow (images).

    Images above `max_megapixels` are only measured, never decoded. A PDF page is measured from
    its size in points (never rendered); only the first `max_pages` pages are measured, because a
    PDF with more pages is refused anyway.
    """

    def __init__(self, max_megapixels: int = 100, max_pages: int = 100) -> None:
        self._max_megapixels = Decimal(max_megapixels)
        self._max_pages = max_pages

    def inspect(self, path: Path) -> FileFacts:
        size = path.stat().st_size
        with path.open("rb") as handle:
            kind = detect_kind(handle.read(_SIGNATURE_BYTES))
        if kind is FileKind.PDF:
            return self._inspect_pdf(path, size)
        if kind in _FORMAT_BY_KIND:
            return self._inspect_image(path, kind, size)
        return FileFacts(kind, size, None, None, False, False, False)

    def _inspect_pdf(self, path: Path, size: int) -> FileFacts:
        def unreadable() -> FileFacts:
            return FileFacts(FileKind.PDF, size, None, None, False, False, False)

        try:
            doc = pymupdf.open(path, filetype="pdf")
        except Exception:
            return unreadable()
        try:
            if doc.needs_pass or doc.is_encrypted:
                return FileFacts(FileKind.PDF, size, None, None, False, True, True)
            try:
                pages = doc.page_count
                active = doc.embfile_count() > 0 or _has_active_objects(doc) or _has_launch(doc)
                largest = _largest_page_megapixels(doc, min(pages, self._max_pages))
            except Exception:
                return unreadable()
            return FileFacts(FileKind.PDF, size, pages, None, active, False, True, largest)
        finally:
            doc.close()

    def _inspect_image(self, path: Path, kind: FileKind, size: int) -> FileFacts:
        def facts(megapixels: Decimal | None, readable: bool) -> FileFacts:
            return FileFacts(kind, size, None, megapixels, False, False, readable)

        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", Image.DecompressionBombWarning)
                with Image.open(path) as image:
                    if image.format != _FORMAT_BY_KIND[kind]:
                        return facts(None, False)
                    megapixels = Decimal(image.width * image.height) / Decimal(1_000_000)
                    if megapixels > self._max_megapixels:
                        return facts(megapixels, True)
                    image.verify()
                if kind is FileKind.JPEG:
                    _decode_scaled_down(path)
        except Image.DecompressionBombError:
            return facts(BOMB_MEGAPIXELS, True)
        except Exception:
            return facts(None, False)
        return facts(megapixels, True)


def _largest_page_megapixels(doc: pymupdf.Document, pages: int) -> Decimal | None:
    """The largest of the first `pages` pages drawn at the OCR resolution, in megapixels."""
    largest = Decimal(0)
    for number in range(pages):
        rect = doc[number].rect
        pixels = Decimal(str(rect.width)) * Decimal(str(rect.height)) * _PIXELS_PER_POINT_SQ
        largest = max(largest, pixels / Decimal(1_000_000))
    return largest if pages else None


def _decode_scaled_down(path: Path) -> None:
    """Decode a JPEG at 1/8 scale (cheap) so truncated data is detected."""
    with Image.open(path) as image:
        image.draft("RGB", (max(1, image.width // _JPEG_DRAFT_DIVISOR),) * 2)
        image.load()


def _has_active_objects(doc: pymupdf.Document) -> bool:
    for xref in range(1, doc.xref_length()):
        try:
            description = doc.xref_object(xref, compressed=True)
        except Exception:
            continue
        if _ACTIVE_OBJECT.search(description):
            return True
    return False


def _has_launch(doc: pymupdf.Document) -> bool:
    return any(
        link.get("kind") == pymupdf.LINK_LAUNCH for page in doc for link in page.get_links()
    )
