"""Original pages of the Comprovante, attached without changing their content (CMP-03).

A page goes into a sheet as tall as the original plus a strip of `STRIP_HEIGHT` points: the
original keeps the area `(0, 0, w, h)` and the number of the Comprovante page is written in the
strip below it, never over the original. The divider of the strip is drawn inside the strip, so
no pixel of the original area changes.
"""

from pathlib import Path
from uuid import UUID

import pymupdf
from PIL import Image

from app.domain.entities.generated import GenerationAlert, GenerationAlertCode, GenerationCode
from app.domain.rules.comprovante_plan import PNG_MAX_MEGAPIXELS, ComprovanteRefused
from app.infrastructure.documents.front_matter import page_label

STRIP_HEIGHT = 24.0
_DIVIDER_Y = 0.5  # inside the strip, so a half-point line never touches the original
_LABEL_SIZE = 9.0
_LABEL_COLOR = (0.2, 0.2, 0.2)
_DIVIDER_COLOR = (0.6, 0.6, 0.6)
RASTER_DPI = 200
RASTER_JPEG_QUALITY = 92
DEFAULT_IMAGE_DPI = 150  # for an image file that does not say its resolution
MAX_PAGE_POINTS = 14_400  # the largest side a PDF page may have
_POINTS_PER_INCH = 72
_EDGE_TOLERANCE = 0.01


def _draw_strip(page: pymupdf.Page, width: float, height: float, number: int) -> None:
    page.draw_line(
        pymupdf.Point(0, height + _DIVIDER_Y),
        pymupdf.Point(width, height + _DIVIDER_Y),
        color=_DIVIDER_COLOR,
        width=0.5,
    )
    area = pymupdf.Rect(0, height + 4, width, height + STRIP_HEIGHT)
    page.insert_textbox(
        area,
        page_label(number),
        fontsize=_LABEL_SIZE,
        fontname="helv",
        color=_LABEL_COLOR,
        align=pymupdf.TEXT_ALIGN_CENTER,
    )


def _place(out: pymupdf.Document, src: pymupdf.Document, pno: int, number: int) -> None:
    rect = src[pno].rect
    width, height = rect.width, rect.height
    page = out.new_page(width=width, height=height + STRIP_HEIGHT)
    page.show_pdf_page(pymupdf.Rect(0, 0, width, height), src, pno)
    _draw_strip(page, width, height, number)


def _needs_preparation(page: pymupdf.Page) -> bool:
    """`show_pdf_page` drops the rotation, the annotations and the fields of a page."""
    return page.rotation != 0 or page.first_annot is not None or page.first_widget is not None


def _prepared(src: pymupdf.Document, pno: int) -> pymupdf.Document:
    """A one-page copy with the annotations and fields drawn into the content and the rotation
    turned into the geometry of the page, so `show_pdf_page` carries all of it over."""
    copy = pymupdf.open()
    copy.insert_pdf(src, from_page=pno, to_page=pno, annots=True, widgets=True)
    copy.bake(annots=True, widgets=True)
    copy[0].remove_rotation()
    return copy


def _crop_is_smaller(page: pymupdf.Page) -> bool:
    crop, media = page.cropbox, page.mediabox
    narrower = crop.width < media.width - _EDGE_TOLERANCE
    shorter = crop.height < media.height - _EDGE_TOLERANCE
    return narrower or shorter


def _rasterize(out: pymupdf.Document, src: pymupdf.Document, pno: int, number: int) -> None:
    """The visible page as one JPEG at `RASTER_DPI`: the last resort for a rotated page with a
    crop, which `remove_rotation` cannot carry over unchanged."""
    page = src[pno]
    picture = page.get_pixmap(dpi=RASTER_DPI, alpha=False).tobytes(
        "jpeg", jpg_quality=RASTER_JPEG_QUALITY
    )
    width, height = page.rect.width, page.rect.height
    sheet = out.new_page(width=width, height=height + STRIP_HEIGHT)
    sheet.insert_image(pymupdf.Rect(0, 0, width, height), stream=picture)
    _draw_strip(sheet, width, height, number)


def attach(
    out: pymupdf.Document,
    src: pymupdf.Document,
    pno: int,
    number: int,
    document_name: str = "documento",
) -> GenerationAlert | None:
    """Appends page `pno` (0-based) of `src` to `out`, numbered `number` in the strip.

    A rotated page whose crop is smaller than the page goes in as a picture (CMP-12) and the
    alert `PAGINA_RASTERIZADA` names the document and the page; any other page goes in as it is.
    """
    page = src[pno]
    if page.rotation != 0 and _crop_is_smaller(page):
        _rasterize(out, src, pno, number)
        return GenerationAlert(
            GenerationAlertCode.PAGINA_RASTERIZADA,
            f"A página {pno + 1} de {document_name} foi anexada como imagem "
            "(página girada com área de recorte).",
        )
    if not _needs_preparation(page):
        _place(out, src, pno, number)
        return None
    copy = _prepared(src, pno)
    try:
        _place(out, copy, 0, number)
    finally:
        copy.close()
    return None


def _image_page_points(width_px: int, height_px: int, dpi: tuple[float, float] | None):
    """Width and height in points of the page of an image: its pixels at its dpi (150 when it
    has none), scaled down to fit `MAX_PAGE_POINTS`."""
    x_dpi, y_dpi = dpi if dpi and min(dpi) > 0 else (DEFAULT_IMAGE_DPI, DEFAULT_IMAGE_DPI)
    width = width_px / x_dpi * _POINTS_PER_INCH
    height = height_px / y_dpi * _POINTS_PER_INCH
    scale = min(1.0, MAX_PAGE_POINTS / max(width, height))
    return width * scale, height * scale


# EXIF orientation of a JPEG -> degrees clockwise that show it upright (CMP-08). The mirrored values
# (2, 4, 5, 7, front cameras) are left as stored: a page cannot mirror a picture without
# decoding it.
_EXIF_ORIENTATION = 0x0112
_EXIF_TURN = {3: 180, 6: 90, 8: 270}


def attach_image(
    out: pymupdf.Document,
    path: Path,
    number: int,
    *,
    document_id: UUID | None = None,
    png_max_megapixels: int = PNG_MAX_MEGAPIXELS,
) -> None:
    """Appends the JPEG or PNG at `path` as one page the size of the picture (CMP-08).

    Only the header is read to measure it; PyMuPDF embeds a JPEG with its own bytes, while a PNG
    is decoded whole, so a PNG above `png_max_megapixels` is refused before anything is decoded
    (CMP-13). A JPEG whose EXIF orientation says it was shot on its side (3, 6 or 8) is turned in
    the page, so it shows upright and its bytes are still the ones of the file.
    """
    with Image.open(path) as image:
        pixels = (image.width, image.height)
        is_png = image.format == "PNG"
        dpi = image.info.get("dpi")
        # the JPEG header is enough to know how the camera held the phone; a PNG would be decoded
        orientation = image.getexif().get(_EXIF_ORIENTATION) if image.format == "JPEG" else None
    if is_png and pixels[0] * pixels[1] > png_max_megapixels * 1_000_000:
        raise ComprovanteRefused(
            GenerationCode.IMAGEM_GRANDE_DEMAIS,
            f"A imagem tem mais de {png_max_megapixels} megapixels.",
            document_id,
        )
    turn = _EXIF_TURN.get(orientation, 0)
    if turn in (90, 270):  # the page is the picture turned on its side: width and height swap
        pixels = (pixels[1], pixels[0])
        dpi = (dpi[1], dpi[0]) if dpi else None
    width, height = _image_page_points(*pixels, dpi)
    sheet = out.new_page(width=width, height=height + STRIP_HEIGHT)
    sheet.insert_image(pymupdf.Rect(0, 0, width, height), filename=str(path), rotate=-turn)
    _draw_strip(sheet, width, height, number)
