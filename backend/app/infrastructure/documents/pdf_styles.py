"""Font, styles and margins of the PDFs generated with reportlab (TAB-01).

The font is Liberation Serif, versioned in `fonts/` with its license (SIL OFL 1.1): the slim
image has no fonts and Liberation Serif has the metrics of Times New Roman, which the model of
the report asks for. reportlab embeds only the glyphs used (a subset).
"""

from dataclasses import dataclass
from pathlib import Path

from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas

from app.domain.entities.report import PageSetup

FONTS_DIR = Path(__file__).parent / "fonts"
FONT_REGULAR = "LiberationSerif"
FONT_BOLD = "LiberationSerif-Bold"
FONT_ITALIC = "LiberationSerif-Italic"
FONT_BOLD_ITALIC = "LiberationSerif-BoldItalic"
_FILES = {
    FONT_REGULAR: "LiberationSerif-Regular.ttf",
    FONT_BOLD: "LiberationSerif-Bold.ttf",
    FONT_ITALIC: "LiberationSerif-Italic.ttf",
    FONT_BOLD_ITALIC: "LiberationSerif-BoldItalic.ttf",
}
LEADING_FACTOR = 1.2


def register_fonts() -> None:
    """Registers the four faces and the family, so `<b>` and `<i>` pick the right face."""
    if FONT_REGULAR in pdfmetrics.getRegisteredFontNames():
        return
    for name, file in _FILES.items():
        pdfmetrics.registerFont(TTFont(name, str(FONTS_DIR / file)))
    pdfmetrics.registerFontFamily(
        FONT_REGULAR,
        normal=FONT_REGULAR,
        bold=FONT_BOLD,
        italic=FONT_ITALIC,
        boldItalic=FONT_BOLD_ITALIC,
    )


class PdfCanvas(Canvas):
    """A canvas whose initial font is Liberation Serif, so no other font is listed in the PDF."""

    def __init__(self, *args, **kwargs) -> None:
        register_fonts()
        if kwargs.get("initialFontName") is None:  # a document template passes None
            kwargs["initialFontName"] = FONT_REGULAR
        super().__init__(*args, **kwargs)


class NumberedCanvas(PdfCanvas):
    """Writes `Página N de M` at the foot of every page; M is only known at the end, so the pages
    are kept until `save` (a second pass over the pages, never over the content)."""

    FOOTER_SIZE = 8

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._saved_pages: list[dict] = []

    def showPage(self) -> None:  # noqa: N802 (reportlab API)
        self._saved_pages.append(dict(self.__dict__))
        self._startPage()

    def save(self) -> None:
        total = len(self._saved_pages)
        for state in self._saved_pages:
            self.__dict__.update(state)
            self._draw_footer(total)
            super().showPage()
        super().save()

    def _draw_footer(self, total: int) -> None:
        width = self._pagesize[0]
        self.setFont(FONT_REGULAR, self.FOOTER_SIZE)
        self.drawCentredString(width / 2, 12 * mm, f"Página {self._pageNumber} de {total}")


@dataclass(frozen=True)
class PageMargins:
    """Margins in points."""

    left: float
    right: float
    top: float
    bottom: float


def margins_from_page(page: PageSetup) -> PageMargins:
    return PageMargins(
        left=page.margin_left_mm * mm,
        right=page.margin_right_mm * mm,
        top=page.margin_top_mm * mm,
        bottom=page.margin_bottom_mm * mm,
    )


@dataclass(frozen=True)
class PdfStyles:
    """The paragraph styles of the generated PDFs, all in Liberation Serif."""

    body: ParagraphStyle
    body_left: ParagraphStyle
    bullet: ParagraphStyle
    title: ParagraphStyle
    heading: ParagraphStyle
    subheading: ParagraphStyle
    header_line: ParagraphStyle
    cell: ParagraphStyle
    cell_header: ParagraphStyle
    band: ParagraphStyle


def _style(name: str, size: float, font: str = FONT_REGULAR, **kwargs) -> ParagraphStyle:
    return ParagraphStyle(
        name, fontName=font, fontSize=size, leading=size * LEADING_FACTOR, **kwargs
    )


def build_styles(font_size: float) -> PdfStyles:
    """Styles at `font_size` points (9 in the report model); titles are a little larger."""
    register_fonts()
    return PdfStyles(
        body=_style("body", font_size, alignment=TA_JUSTIFY, spaceAfter=font_size / 2),
        body_left=_style("body_left", font_size, alignment=TA_LEFT),
        bullet=_style(
            "bullet", font_size, alignment=TA_JUSTIFY, leftIndent=font_size * 1.5, bulletIndent=0
        ),
        title=_style("title", font_size + 3, FONT_BOLD, alignment=TA_CENTER, spaceAfter=font_size),
        heading=_style(
            "heading", font_size + 1, FONT_BOLD, spaceBefore=font_size, spaceAfter=font_size / 2
        ),
        subheading=_style(
            "subheading", font_size, FONT_BOLD_ITALIC, spaceBefore=font_size / 2, spaceAfter=2
        ),
        header_line=_style("header_line", font_size + 1, FONT_BOLD, alignment=TA_CENTER),
        cell=_style("cell", font_size, alignment=TA_LEFT),
        cell_header=_style("cell_header", font_size, FONT_BOLD, alignment=TA_CENTER),
        band=_style("band", font_size, FONT_BOLD, alignment=TA_LEFT),
    )
