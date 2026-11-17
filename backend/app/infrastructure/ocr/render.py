"""Page rendering and image preprocessing for OCR (PIPE-06).

Both PDF pages (rendered at 300 dpi) and JPG/PNG inputs end as grayscale images with
autocontrast. No OpenCV.
"""

from pathlib import Path

import pymupdf
from PIL import Image, ImageOps

DEFAULT_DPI = 300


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
        pixmap = doc[page_number - 1].get_pixmap(dpi=dpi, colorspace=pymupdf.csGRAY, alpha=False)
        rendered = Image.frombytes("L", (pixmap.width, pixmap.height), pixmap.samples)
    return preprocess(rendered)


def load_image(path: Path) -> Image.Image:
    """Open a JPG or PNG file as a preprocessed grayscale image."""
    with Image.open(path) as image:
        image.load()
        return preprocess(image)
