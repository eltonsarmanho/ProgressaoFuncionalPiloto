"""Original pages of the Comprovante, attached without changing their content (CMP-03).

A page goes into a sheet as tall as the original plus a strip of `STRIP_HEIGHT` points: the
original keeps the area `(0, 0, w, h)` and the number of the Comprovante page is written in the
strip below it, never over the original. The divider of the strip is drawn inside the strip, so
no pixel of the original area changes.
"""

import pymupdf

from app.infrastructure.documents.front_matter import page_label

STRIP_HEIGHT = 24.0
_DIVIDER_Y = 0.5  # inside the strip, so a half-point line never touches the original
_LABEL_SIZE = 9.0
_LABEL_COLOR = (0.2, 0.2, 0.2)
_DIVIDER_COLOR = (0.6, 0.6, 0.6)


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


def attach(out: pymupdf.Document, src: pymupdf.Document, pno: int, number: int) -> None:
    """Appends page `pno` (0-based) of `src` to `out`, numbered `number` in the strip."""
    _place(out, src, pno, number)
