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


def max_difference(first: bytes, second: bytes) -> int:
    """The largest gap between two renderings of the same size, in gray levels."""
    assert len(first) == len(second), "the renderings do not have the same size"
    return max((abs(a - b) for a, b in zip(first, second, strict=True)), default=0)


ANNOTATION_AREA = pymupdf.Rect(320, 560, 520, 640)


def add_annotation(page: pymupdf.Page, kind: str) -> None:
    """One annotation or field inside `ANNOTATION_AREA`: stamp, free text, highlight, a filled
    text field, or an ink stroke standing for the appearance of a signature."""
    area = ANNOTATION_AREA
    if kind == "stamp":
        page.add_stamp_annot(area, stamp=pymupdf.STAMP_Approved)
    elif kind == "freetext":
        page.add_freetext_annot(
            area, "Recebido em teste", fontsize=14, text_color=(0, 0, 1), fill_color=(1, 1, 0.6)
        )
    elif kind == "highlight":
        page.draw_rect(area, color=None, fill=(0.8, 0.8, 0.8))
        page.insert_text((area.x0 + 4, area.y0 + 30), "Trecho destacado", fontsize=14)
        page.add_highlight_annot(pymupdf.Rect(area.x0, area.y0 + 15, area.x1, area.y0 + 36))
    elif kind == "field":
        widget = pymupdf.Widget()
        widget.field_type = pymupdf.PDF_WIDGET_TYPE_TEXT
        widget.field_name = "nome"
        widget.rect = area
        widget.field_value = "Fulana Exemplo"
        widget.text_fontsize = 14
        page.add_widget(widget)
    elif kind == "signature":
        stroke = [
            [(area.x0 + 5 + 8 * i, area.y0 + 40 + (-1) ** i * 20) for i in range(20)],
        ]
        annot = page.add_ink_annot(stroke)
        annot.set_border(width=3)
        annot.set_colors(stroke=(0, 0, 0.6))
        annot.update()
    else:
        raise ValueError(kind)


def write_image(path, fmt: str, size: tuple[int, int], dpi=None, mode: str = "RGB") -> bytes:
    """A flat-color image file of `fmt` (JPEG or PNG) with the given pixels and dpi; flat colors
    keep the file small, so a very large picture costs the test no memory to store."""
    image = Image.new(mode, size, 255 if mode in ("L", "1") else (200, 120, 40))
    options = {} if dpi is None else {"dpi": (dpi, dpi)}
    image.save(path, format=fmt, **options)
    return path.read_bytes()


def write_png_header_only(path, size: tuple[int, int]) -> None:
    """A PNG with a header of `size` and picture data that is not data: Pillow can read its
    dimensions, but nothing can decode it."""
    import struct
    import zlib

    def chunk(kind: bytes, data: bytes) -> bytes:
        crc = struct.pack(">I", zlib.crc32(kind + data))
        return struct.pack(">I", len(data)) + kind + data + crc

    header = struct.pack(">IIBBBBB", size[0], size[1], 8, 0, 0, 0, 0)
    body = chunk(b"IHDR", header) + chunk(b"IDAT", b"not a picture") + chunk(b"IEND", b"")
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + body)
