"""Synthetic scanned documents: one JPEG per page, every page different (no real document)."""

import io
from functools import cache
from pathlib import Path

import pymupdf
from PIL import Image, ImageChops

SCAN_SIZE = (1240, 1754)  # A4 at 150 dpi
_NOISE_SIGMA = 8  # with JPEG quality 75 an RGB page takes about 222 KB
_QUALITY = 75
A4_POINTS = (595.0, 842.0)


@cache
def _noise() -> Image.Image:
    return Image.effect_noise(SCAN_SIZE, _NOISE_SIGMA)


def scanned_page_jpeg(index: int) -> bytes:
    """A different JPEG for every `index`: noise shifted by a different offset."""
    base = _noise()
    picture = Image.merge(
        "RGB",
        (
            ImageChops.offset(base, index + 1, 2 * index + 1),
            ImageChops.offset(base, index + 7, index + 3),
            ImageChops.offset(base, 3 * index + 3, index + 9),
        ),
    )
    buffer = io.BytesIO()
    picture.save(buffer, format="JPEG", quality=_QUALITY)
    return buffer.getvalue()


def write_scanned_pdf(path: Path, pages: int, first_index: int) -> None:
    """A PDF of `pages` A4 pages, each with a full-page scan."""
    doc = pymupdf.open()
    for number in range(pages):
        page = doc.new_page(width=A4_POINTS[0], height=A4_POINTS[1])
        page.insert_image(page.rect, stream=scanned_page_jpeg(first_index + number))
    doc.save(path)
    doc.close()
