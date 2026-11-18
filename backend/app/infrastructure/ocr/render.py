"""Page rendering and image preprocessing for OCR (PIPE-06).

Both PDF pages (rendered at 300 dpi) and JPG/PNG inputs end as grayscale images with
autocontrast. No OpenCV. A page that would need more than `MAX_RENDER_MEGAPIXELS` at 300 dpi is
drawn at a lower resolution (VER-02); one that would need less than `MIN_DPI` is refused.
"""

import math
from pathlib import Path

import pymupdf
from PIL import Image, ImageOps

DEFAULT_DPI = 300
MAX_RENDER_MEGAPIXELS = 50
MIN_DPI = 72
_POINTS_PER_INCH = 72


class PageTooLarge(Exception):
    """The page cannot be drawn within the pixel cap even at the minimum resolution."""


def preprocess(image: Image.Image) -> Image.Image:
    """Grayscale (transparency over white) with autocontrast; the input is left untouched."""
    if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
        rgba = image.convert("RGBA")
        background = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        image = Image.alpha_composite(background, rgba)
    return ImageOps.autocontrast(image.convert("L"))


def render_page(path: Path, page_number: int, dpi: int = DEFAULT_DPI) -> Image.Image:
    """Render a PDF page (1-based) at `dpi` as a preprocessed grayscale image."""
    with pymupdf.open(path, filetype="pdf") as doc:
        page = doc[page_number - 1]
        dpi = _dpi_within_cap(page.rect, dpi)
        pixmap = page.get_pixmap(dpi=dpi, colorspace=pymupdf.csGRAY, alpha=False)
        rendered = Image.frombytes("L", (pixmap.width, pixmap.height), pixmap.samples)
    return preprocess(rendered)


def _dpi_within_cap(rect: pymupdf.Rect, dpi: int) -> int:
    """`dpi` lowered to keep the page within `MAX_RENDER_MEGAPIXELS`; PageTooLarge under MIN_DPI."""
    area_in2 = (rect.width / _POINTS_PER_INCH) * (rect.height / _POINTS_PER_INCH)
    if area_in2 * dpi * dpi <= MAX_RENDER_MEGAPIXELS * 1_000_000:
        return dpi
    capped = math.floor(math.sqrt(MAX_RENDER_MEGAPIXELS * 1_000_000 / area_in2))
    if capped < MIN_DPI:
        raise PageTooLarge("page too large to draw")
    return capped


def load_image(path: Path) -> Image.Image:
    """Open a JPG or PNG file as a preprocessed grayscale image."""
    with Image.open(path) as image:
        image.load()
        return preprocess(image)
