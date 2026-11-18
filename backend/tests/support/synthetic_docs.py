"""Synthetic documents for tests (ACC-03). Every text is invented: fake names, no real ID numbers.

Each generator returns the file bytes. Image text uses a font size large enough for Tesseract.
"""

import io
import textwrap
from collections.abc import Sequence

import pymupdf
from PIL import Image, ImageDraw, ImageFont

FAKE_PROFESSOR = "Fulana de Tal Exemplo"
FAKE_SIAPE = "0000000"
FAKE_CPF = "000.000.000-00"

SAMPLE_PAGES = (
    "DECLARACAO DE BANCA EXAMINADORA\n"
    f"Declaramos que {FAKE_PROFESSOR}, matricula SIAPE {FAKE_SIAPE}, participou como membro da "
    "banca examinadora do trabalho de conclusao de curso Estudo Ficticio sobre Dados Abertos, "
    "realizada em 12 de marco de 2025, na Faculdade Exemplo de Testes.",
)

_PDF_MARGIN = 50
_FONT_SIZE_PT = 12
_IMAGE_FONT_SIZE = 40
_PAGE_WIDTH_PX = 2480  # A4 at 300 dpi
_PAGE_HEIGHT_PX = 3508
_WRAP_CHARS = 85


def _new_pdf(pages: Sequence[str]) -> pymupdf.Document:
    doc = pymupdf.open()
    for text in pages:
        page = doc.new_page()
        rect = pymupdf.Rect(_PDF_MARGIN, _PDF_MARGIN, page.rect.width - _PDF_MARGIN, 780)
        page.insert_textbox(rect, text, fontsize=_FONT_SIZE_PT, fontname="helv")
    return doc


def _pdf_bytes(doc: pymupdf.Document, **save_options) -> bytes:
    data = doc.tobytes(**save_options)
    doc.close()
    return data


def _render_text(text: str, width: int, height: int) -> Image.Image:
    image = Image.new("L", (width, height), 255)
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=_IMAGE_FONT_SIZE)
    lines: list[str] = []
    for paragraph in text.split("\n"):
        lines.extend(textwrap.wrap(paragraph, _WRAP_CHARS) or [""])
    y = 120
    for line in lines:
        draw.text((120, y), line, fill=0, font=font)
        y += _IMAGE_FONT_SIZE + 24
    return image


def _encode(image: Image.Image, fmt: str) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format=fmt)
    return buffer.getvalue()


def pdf_with_text(pages: Sequence[str] = SAMPLE_PAGES) -> bytes:
    """PDF whose pages carry a normal text layer."""
    return _pdf_bytes(_new_pdf(pages))


def pdf_scanned(pages: Sequence[str] = SAMPLE_PAGES) -> bytes:
    """PDF with one image per page and no text layer."""
    doc = pymupdf.open()
    for text in pages:
        page = doc.new_page()
        picture = _encode(_render_text(text, _PAGE_WIDTH_PX, _PAGE_HEIGHT_PX), "PNG")
        page.insert_image(page.rect, stream=picture)
    return _pdf_bytes(doc)


def pdf_mixed(text_page: str = SAMPLE_PAGES[0], scanned_page: str = SAMPLE_PAGES[0]) -> bytes:
    """Two pages: the first has a text layer, the second is a scanned image."""
    doc = _new_pdf([text_page])
    page = doc.new_page()
    picture = _encode(_render_text(scanned_page, _PAGE_WIDTH_PX, _PAGE_HEIGHT_PX), "PNG")
    page.insert_image(page.rect, stream=picture)
    return _pdf_bytes(doc)


def pdf_header_footer_over_image_body(
    header: str = "UNIVERSIDADE FEDERAL EXEMPLAR - Pro-Reitoria de Extensao - Certificado",
    footer: str = "Documento ficticio do sistema de testes, validacao em endereco ficticio",
    body: str = SAMPLE_PAGES[0],
    image_covers_page: bool = True,
) -> bytes:
    """One page with a text header and footer and the body as a picture (raster certificate)."""
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_textbox(pymupdf.Rect(50, 20, page.rect.width - 50, 60), header, fontsize=10)
    page.insert_textbox(
        pymupdf.Rect(50, page.rect.height - 60, page.rect.width - 50, page.rect.height - 20),
        footer,
        fontsize=10,
    )
    picture = _encode(_render_text(body, _PAGE_WIDTH_PX, _PAGE_HEIGHT_PX), "PNG")
    area = page.rect if image_covers_page else pymupdf.Rect(50, 100, 150, 160)
    page.insert_image(area, stream=picture)
    return _pdf_bytes(doc)


def jpg_with_text(text: str = SAMPLE_PAGES[0]) -> bytes:
    return _encode(_render_text(text, _PAGE_WIDTH_PX, _PAGE_HEIGHT_PX), "JPEG")


def png_with_text(text: str = SAMPLE_PAGES[0]) -> bytes:
    return _encode(_render_text(text, _PAGE_WIDTH_PX, _PAGE_HEIGHT_PX), "PNG")


def noisy_text() -> str:
    """Text shaped like the garbage layer of real decree PDFs: more than 30% symbols."""
    noise = "~^<>|[]{}*=_`$"
    lines = []
    for number in range(8):
        glyphs = "".join(noise[(number + i) % len(noise)] for i in range(12))
        lines.append(f"7 r{glyphs[:4]}rjo{glyphs[4:8]}N *P{glyphs[8:]}44 portaria {number}")
    return "\n".join(lines)


def pdf_noisy_text_layer() -> bytes:
    """PDF whose text layer is mostly symbols."""
    return _pdf_bytes(_new_pdf([noisy_text()]))


def pdf_with_javascript() -> bytes:
    """PDF with a JavaScript open action."""
    doc = _new_pdf(SAMPLE_PAGES)
    catalog = doc.pdf_catalog()
    doc.xref_set_key(catalog, "OpenAction", "<< /S /JavaScript /JS (app.alert\\('teste'\\);) >>")
    return _pdf_bytes(doc)


def pdf_encrypted() -> bytes:
    """PDF protected by a password."""
    doc = _new_pdf(SAMPLE_PAGES)
    return _pdf_bytes(
        doc,
        encryption=pymupdf.PDF_ENCRYPT_AES_256,
        user_pw="senha-de-teste",
        owner_pw="senha-do-dono",
    )


def pdf_with_embedded_file() -> bytes:
    """PDF carrying an embedded attachment."""
    doc = _new_pdf(SAMPLE_PAGES)
    doc.embfile_add("anexo.txt", b"conteudo ficticio do anexo")
    return _pdf_bytes(doc)


def png_huge() -> bytes:
    """All-white PNG above 100 megapixels that stays small on disk."""
    return _encode(Image.new("1", (11000, 10000), 1), "PNG")


def pdf_with_page_size(width_pt: float, height_pt: float, extra_pages: Sequence[str] = ()) -> bytes:
    """Tiny PDF whose first page has the given size in points (a huge page stays small on disk).

    `extra_pages` are normal A4 pages after it.
    """
    doc = pymupdf.open()
    doc.new_page(width=width_pt, height=height_pt)
    for text in extra_pages:
        page = doc.new_page()
        page.insert_text((50, 80), text, fontsize=_FONT_SIZE_PT)
    return _pdf_bytes(doc)
