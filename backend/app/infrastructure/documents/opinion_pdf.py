"""The Parecer as PDF, drawn with reportlab (PMOD-01, PMOD-02, PMOD-04 to PMOD-07, PMOD-21).

Same model and same order as the DOCX: A4 portrait with the margins of the page of the model and
12 pt text, the emblem of the UFPA on top of the first page (BRAS-04), the header centered in
Liberation Serif with a rule across the text width, the title and the place and date line in
Liberation Sans, the justified paragraph with its bold runs, and the centered member lines. No
table and no page footer (`PdfCanvas`, not `NumberedCanvas`). The text is the one of the
`OpinionDocument`; nothing is composed here.
"""

from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import BaseDocTemplate, Frame, HRFlowable, PageTemplate, Paragraph

from app.domain.rules.opinion_document import OpinionDocument, TextRun
from app.infrastructure.documents.pdf_styles import (
    FONT_REGULAR,
    FONT_SANS,
    FONT_SANS_BOLD,
    PdfCanvas,
    emblem_flowables,
    margins_from_page,
    register_fonts,
)
from app.infrastructure.documents.text_safety import xml_safe

_BODY_PT = 12
_LINE_SPACING = 1.5
_FIRST_LINE_INDENT = 1.25 * cm
_RULE_PT = 0.75


def _text(text: str) -> str:
    return escape(xml_safe(text))


def _markup(runs: tuple[TextRun, ...]) -> str:
    return "".join(f"<b>{_text(r.text)}</b>" if r.bold else _text(r.text) for r in runs)


def _style(name: str, font: str = FONT_REGULAR, **kwargs) -> ParagraphStyle:
    kwargs.setdefault("leading", _BODY_PT * 1.2)
    return ParagraphStyle(name, fontName=font, fontSize=_BODY_PT, **kwargs)


def write_opinion_pdf(model: OpinionDocument, target: Path) -> None:
    """Writes the PDF to `target` (a path, never a stream)."""
    register_fonts()
    margins = margins_from_page(model.page)
    width = A4[0] - margins.left - margins.right
    header = _style("opinion_header", alignment=TA_CENTER)
    title = _style(
        "opinion_title",
        FONT_SANS_BOLD,
        alignment=TA_CENTER,
        spaceBefore=_BODY_PT,
        spaceAfter=2 * _BODY_PT,
    )
    place_date = _style(
        "opinion_place_date",
        FONT_SANS,
        alignment=TA_LEFT,
        leftIndent=width / 2,
        spaceAfter=2 * _BODY_PT,
    )
    body = _style(
        "opinion_body",
        alignment=TA_JUSTIFY,
        firstLineIndent=_FIRST_LINE_INDENT,
        leading=_BODY_PT * _LINE_SPACING,
        spaceAfter=3 * _BODY_PT,
    )
    member = _style("opinion_member", alignment=TA_CENTER, spaceAfter=_BODY_PT / 2)
    template = BaseDocTemplate(
        str(target),
        pagesize=A4,
        leftMargin=margins.left,
        rightMargin=margins.right,
        topMargin=margins.top,
        bottomMargin=margins.bottom,
        title=model.title,
    )
    # No padding in the frame: the text, the rule and the half-width indent start at the margins.
    frame = Frame(
        margins.left,
        margins.bottom,
        width,
        A4[1] - margins.top - margins.bottom,
        leftPadding=0,
        rightPadding=0,
        topPadding=0,
        bottomPadding=0,
    )
    template.addPageTemplates([PageTemplate(id="opinion", frames=[frame])])
    story: list = [*emblem_flowables()]
    story += [Paragraph(_text(line), header) for line in model.header_lines]
    story += [
        HRFlowable(
            width="100%",
            thickness=_RULE_PT,
            color=colors.black,
            spaceBefore=_BODY_PT / 2,
            spaceAfter=0,
        ),
        Paragraph(_text(model.title), title),
        Paragraph(_text(model.place_date_line), place_date),
        Paragraph(_markup(model.paragraph), body),
    ]
    story += [Paragraph(_text(line), member) for line in model.member_lines]
    template.build(story, canvasmaker=PdfCanvas)
