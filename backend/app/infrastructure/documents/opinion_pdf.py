"""The Parecer as PDF, drawn with reportlab (PAR-03).

Same model and same order as the DOCX: A4 portrait with the margins and the font size of the
page of the model, the institutional header and the title centered, each section with its
heading and lines, the table of points closed by the Total geral, one signature line for each
member, and `Página N de M` at the foot. The numbers and the text are the ones of the
`OpinionDocument`; nothing is summed or written here.
"""

from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.domain.rules.opinion_document import OpinionDocument, OpinionSection, Signature
from app.infrastructure.documents.pdf_styles import (
    FONT_REGULAR,
    NumberedCanvas,
    PdfStyles,
    build_styles,
    margins_from_page,
)
from app.infrastructure.documents.text_safety import xml_safe

_SIGNATURE_RULE = "_" * 42
_SIGNATURE_GAP = 30
_VALUE_WIDTH = 85  # points
_GREY = colors.Color(0.9, 0.9, 0.9)
_LINE = colors.Color(0.4, 0.4, 0.4)
_JUSTIFIED = {"conclusao", "observacoes"}


def _p(text: str, style) -> Paragraph:
    return Paragraph(escape(xml_safe(text)), style)


def _points_table(section: OpinionSection, styles: PdfStyles, width: float) -> Table:
    value_style = ParagraphStyle("cell_right", parent=styles.cell, alignment=TA_RIGHT)
    value_band = ParagraphStyle("band_right", parent=styles.band, alignment=TA_RIGHT)
    rows = [[_p(r.label, styles.cell), _p(r.value, value_style)] for r in section.rows]
    commands = [
        ("FONTNAME", (0, 0), (-1, -1), FONT_REGULAR),
        ("GRID", (0, 0), (-1, -1), 0.25, _LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]
    if section.total is not None:
        last = len(rows)
        rows.append([_p(section.total.label, styles.band), _p(section.total.value, value_band)])
        commands.append(("BACKGROUND", (0, last), (-1, last), _GREY))
    table = Table(rows, colWidths=[width - _VALUE_WIDTH, _VALUE_WIDTH])
    table.setStyle(TableStyle(commands))
    return table


def _section(section: OpinionSection, styles: PdfStyles, width: float) -> list:
    story = []
    if section.heading:
        story.append(_p(section.heading, styles.heading))
    style = styles.body if section.key in _JUSTIFIED else styles.body_left
    for text in section.lines:
        story.extend(_p(line, style) for line in xml_safe(text).split("\n"))
    if section.rows or section.total is not None:
        story.append(_points_table(section, styles, width))
    return story


def _signature(signature: Signature, styles: PdfStyles) -> KeepTogether:
    centered = ParagraphStyle("signature", parent=styles.header_line, fontName=FONT_REGULAR)
    return KeepTogether(
        [
            Spacer(1, _SIGNATURE_GAP),
            _p(_SIGNATURE_RULE, centered),
            _p(signature.name, styles.header_line),
            _p(signature.role, centered),
        ]
    )


def write_opinion_pdf(model: OpinionDocument, target: Path) -> None:
    """Writes the PDF to `target` (a path, never a stream)."""
    page = model.page
    styles = build_styles(page.font_size_pt)
    margins = margins_from_page(page)
    template = SimpleDocTemplate(
        str(target),
        pagesize=A4,
        leftMargin=margins.left,
        rightMargin=margins.right,
        topMargin=margins.top,
        bottomMargin=margins.bottom,
        title=model.title,
    )
    width = A4[0] - margins.left - margins.right
    story: list = [_p(line, styles.header_line) for line in model.header_lines]
    story += [Spacer(1, 6), _p(model.title, styles.title)]
    for section in model.sections:
        story += _section(section, styles, width)
    story += [_signature(signature, styles) for signature in model.signatures]
    template.build(story, canvasmaker=NumberedCanvas)
