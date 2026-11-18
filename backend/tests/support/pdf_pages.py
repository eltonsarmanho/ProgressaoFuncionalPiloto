"""Synthetic source pages for the tests of the Comprovante: text, JPEG pictures, rotation,
annotations and fields, all invented (no real document)."""

import io
import random

import pymupdf
from PIL import Image

A4 = (595.0, 842.0)


def noise_jpeg(width: int = 240, height: int = 320, seed: int = 1, quality: int = 85) -> bytes:
    """A JPEG of random pixels: it does not compress, so a recompression would show."""
    rng = random.Random(seed)
    image = Image.new("RGB", (width, height))
    image.putdata([(rng.randrange(256), rng.randrange(256), rng.randrange(256))
                   for _ in range(width * height)])  # fmt: skip
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=quality)
    return buffer.getvalue()


def source_pdf(
    pages: int = 3, size: tuple[float, float] = A4, picture: bool = True
) -> pymupdf.Document:
    """Pages with a different text each (`Origem pagina N`) and, optionally, a picture each."""
    doc = pymupdf.open()
    for number in range(1, pages + 1):
        page = doc.new_page(width=size[0], height=size[1])
        page.insert_textbox(
            pymupdf.Rect(40, 40, size[0] - 40, 120),
            f"Origem pagina {number}\nTexto sintetico do documento de teste.",
            fontsize=12,
        )
        page.draw_rect(pymupdf.Rect(30, 30, size[0] - 30, size[1] - 30), color=(0, 0, 0), width=1)
        if picture:
            page.insert_image(pymupdf.Rect(60, 200, 300, 520), stream=noise_jpeg(seed=number))
    return doc


def reopened(doc: pymupdf.Document) -> pymupdf.Document:
    """The document saved and opened again, as the assembler reads an original from disk."""
    return pymupdf.open("pdf", doc.tobytes())


def image_bytes(doc: pymupdf.Document, page_number: int) -> list[bytes]:
    """The bytes of the pictures embedded in a page, in the order of the page."""
    page = doc[page_number]
    return [doc.extract_image(item[0])["image"] for item in page.get_images(full=True)]


def render(page: pymupdf.Page, clip: pymupdf.Rect | None = None, zoom: float = 2.0) -> bytes:
    """The pixels of the page (or of `clip`) at `zoom`, for comparing two renderings."""
    return page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), clip=clip).samples
