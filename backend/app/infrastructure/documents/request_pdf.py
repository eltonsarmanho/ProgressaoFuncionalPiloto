"""The Requerimento as PDF, drawn with reportlab (REQ-02, REQ-03, REQ-05).

Same model and same order as the DOCX: A4 portrait with the margins and the font size of the
page of the model, the institutional header and the title centered, the greeting, the marked
option, the justified paragraph of the request, the evaluation line, place and date, the
closing, the signature line with its caption, the SIAPE and the LGPD note. The emblem of the
UFPA opens the first page (BRAS-05).
"""

from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer

from app.domain.rules.request_document import RequestDocument
from app.infrastructure.documents.pdf_styles import (
    FONT_BOLD,
    FONT_REGULAR,
    PdfCanvas,
    build_styles,
    emblem_flowables,
    margins_from_page,
)
from app.infrastructure.documents.text_safety import xml_safe

_SIGNATURE_GAP = 36
_LGPD_SIZE = 9
_SPACE_AFTER = 8


def _p(text: str, style) -> Paragraph:
    return Paragraph(escape(xml_safe(text)), style)


def write_request_pdf(model: RequestDocument, target: Path) -> None:
    """Writes the PDF to `target` (a path, never a stream)."""
    page = model.page
    size = page.font_size_pt
    styles = build_styles(size)
    margins = margins_from_page(page)
    body = ParagraphStyle("request_body", parent=styles.body_left, spaceAfter=_SPACE_AFTER)
    justified = ParagraphStyle("request_justified", parent=styles.body, spaceAfter=_SPACE_AFTER)
    bold = ParagraphStyle("request_option", parent=body, fontName=FONT_BOLD)
    centered = ParagraphStyle("request_centered", parent=body, alignment=TA_CENTER)
    caption = ParagraphStyle("request_caption", parent=centered, spaceAfter=0)
    lgpd_heading = ParagraphStyle(
        "request_lgpd_heading",
        parent=body,
        fontName=FONT_BOLD,
        fontSize=_LGPD_SIZE,
        leading=_LGPD_SIZE * 1.2,
        spaceBefore=size,
        spaceAfter=2,
    )
    lgpd_text = ParagraphStyle(
        "request_lgpd_text",
        parent=justified,
        fontName=FONT_REGULAR,
        fontSize=_LGPD_SIZE,
        leading=_LGPD_SIZE * 1.2,
    )
    template = SimpleDocTemplate(
        str(target),
        pagesize=A4,
        leftMargin=margins.left,
        rightMargin=margins.right,
        topMargin=margins.top,
        bottomMargin=margins.bottom,
        title=model.title,
    )
    story: list = [*emblem_flowables()]
    story += [_p(line, styles.header_line) for line in model.header_lines]
    story += [
        Spacer(1, size),
        _p(model.title, styles.title),
        _p(model.greeting, body),
        _p(model.option, bold),
        _p(model.request_paragraph, justified),
        _p(model.evaluation_line, justified),
        _p(model.place_date_line, body),
        _p(model.closing, body),
        KeepTogether(
            [
                Spacer(1, _SIGNATURE_GAP),
                _p(model.signature_line, caption),
                _p(model.signature_caption, caption),
                _p(model.siape_line, centered),
            ]
        ),
        _p(model.lgpd_heading, lgpd_heading),
        _p(model.lgpd_text, lgpd_text),
    ]
    template.build(story, canvasmaker=PdfCanvas)
