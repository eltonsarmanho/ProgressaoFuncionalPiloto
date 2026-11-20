"""The activities report as PDF, drawn with reportlab (REL-09, REL-11).

Same model and same order as the DOCX: A4 portrait with the margins of the template, the
institutional header centered, the identification, the sections that have activity, justified
bullet entries and `Página N de M` at the foot. The text of every entry is the text of the draft.
"""

from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import A4
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer

from app.domain.entities.report import DocumentSection, ReportDocument
from app.infrastructure.documents.pdf_styles import (
    NumberedCanvas,
    PdfStyles,
    build_styles,
    margins_from_page,
)
from app.infrastructure.documents.text_safety import xml_safe

BULLET = "•"


def _p(text: str, style, **kwargs) -> Paragraph:
    return Paragraph(escape(xml_safe(text)), style, **kwargs)


def _entry(text: str, styles: PdfStyles) -> KeepTogether:
    """The first line is a bullet; the other lines follow under its text, one paragraph each."""
    lines = xml_safe(text).split("\n")
    parts = []
    for number, line in enumerate(lines):
        last = number == len(lines) - 1
        style = styles.bullet if last else styles.bullet_tight
        parts.append(_p(line, style, bulletText=BULLET if number == 0 else None))
    return KeepTogether(parts)


def _section(section: DocumentSection, styles: PdfStyles) -> list:
    story = [_p(f"{section.key} {section.title}", styles.heading)]
    for line in filter(None, section.free_text.split("\n")):
        story.append(_p(line, styles.body))
    for group in section.groups:
        if group.subtitle:
            story.append(_p(group.subtitle, styles.subheading))
        story.extend(_entry(entry, styles) for entry in group.entries)
    return story


def write_report_pdf(model: ReportDocument, target: Path) -> None:
    """Writes the PDF to `target` (a path, never a stream)."""
    page = model.layout.page
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
    story: list = [_p(line, styles.header_line) for line in model.header_lines]
    story += [Spacer(1, 6), _p(model.title, styles.title)]
    story += [_p(line, styles.body_left) for line in model.identification]
    story += [Spacer(1, 6), _p(model.body_heading, styles.header_line)]
    for section in model.sections:
        story += _section(section, styles)
    template.build(story, canvasmaker=NumberedCanvas)
