"""Cover, table of contents and group separators of the Comprovante, drawn with reportlab
(CMP-01, CMP-04).

The generated pages are written to one PDF in the order of the plan; the assembler takes them
from there, between the original pages. The table of contents is drawn in lines of a fixed height
(a group and an item take one line, an activity two), `TOC_CAPACITY` lines to a page, so the
number of its pages is the arithmetic the plan already did and the renderer only checks it: a
flowing layout would break lines on its own and put the numbers of every later page off.
Lines that do not fit their width end in an ellipsis; an activity may start on one page and end
on the next, because the plan counts lines and not entries.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import Paragraph

from app.domain.entities.comprovante import (
    ComprovantePlan,
    PageKind,
    PlanPage,
    TocEntry,
    TocLevel,
)
from app.domain.repositories.ports import ComprovanteFront
from app.domain.rules.comprovante_plan import NO_VOUCHER_NOTE, remission_text
from app.domain.rules.pt_format import format_interstice
from app.domain.rules.table_document import roman
from app.infrastructure.documents.pdf_styles import (
    FONT_BOLD,
    FONT_ITALIC,
    FONT_REGULAR,
    PdfCanvas,
    build_styles,
)
from app.infrastructure.documents.text_safety import xml_safe

PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN_X = 20 * mm
LINE_HEIGHT = 15.0
_FIRST_LINE_Y = PAGE_HEIGHT - 28 * mm - 44  # baseline of the first line, under the heading
_LAST_LINE_Y = 24 * mm
TOC_CAPACITY = int((_FIRST_LINE_Y - _LAST_LINE_Y) // LINE_HEIGHT) + 1
FOOTER_SIZE = 9
EMPTY_NUMBER = "—"
ELLIPSIS = "…"
_NUMBER_GAP = 10  # between the text of a line and its page number
_INDENT = {TocLevel.GRUPO: 0, TocLevel.ITEM: 12, TocLevel.ATIVIDADE: 24}


def page_label(number: int) -> str:
    """What every page of the Comprovante says at its foot, generated or original."""
    return f"Comprovante p. {number}"


@dataclass(frozen=True)
class _Line:
    text: str
    number: str = ""
    indent: float = 0
    font: str = FONT_REGULAR
    size: float = 10


def _group_title(front: ComprovanteFront, group_number: int) -> str:
    name = front.group_names.get(group_number, "")
    return f"{roman(group_number)}. {name}".strip()


def _item_title(front: ComprovanteFront, group_number: int, item_number: int | None) -> str:
    label = f"{roman(group_number)}.{item_number}"
    name = front.item_names.get((group_number, item_number), "") if item_number else ""
    return f"{label} {name}".strip()


def _number(value: int | None) -> str:
    return EMPTY_NUMBER if value is None else str(value)


def _origin_text(entry: TocEntry, front: ComprovanteFront) -> str:
    """Second line of an activity: where its pages come from and where they are."""
    if not entry.sources:
        return entry.note or NO_VOUCHER_NOTE
    origins = [
        remission_text(ref)
        if ref.remission
        else f"{front.document_names.get(ref.document_id, 'documento')}, p. {ref.source_page}"
        for ref in entry.sources
    ]
    text = "origem: " + "; ".join(origins)
    if entry.first_page is None:
        return text
    pages = f"p. {entry.first_page}"
    if entry.last_page not in (None, entry.first_page):
        pages += f" a {entry.last_page}"
    return f"{text} - Comprovante {pages}"


def toc_lines(plan: ComprovantePlan, front: ComprovanteFront) -> list[_Line]:
    """The lines of the table of contents, in the count the plan used to size it."""
    lines: list[_Line] = []
    for entry in plan.toc:
        indent = _INDENT[entry.level]
        if entry.level is TocLevel.GRUPO:
            title = _group_title(front, entry.group_number)
            lines.append(_Line(title, _number(entry.first_page), indent, FONT_BOLD))
        elif entry.level is TocLevel.ITEM:
            title = _item_title(front, entry.group_number, entry.item_number)
            lines.append(_Line(title, _number(entry.first_page), indent, FONT_BOLD))
        else:
            lines.append(_Line(entry.title, _number(entry.first_page), indent, size=9))
            lines.append(_Line(_origin_text(entry, front), "", indent + 12, FONT_ITALIC, 8))
    return lines


def _fit(text: str, font: str, size: float, width: float) -> str:
    """`text` cut to `width` points, ending in an ellipsis when it had to be cut."""
    text = " ".join(xml_safe(text).split())
    if stringWidth(text, font, size) <= width:
        return text
    while text and stringWidth(text + ELLIPSIS, font, size) > width:
        text = text[:-1]
    return text.rstrip() + ELLIPSIS


def _footer(canvas: PdfCanvas, number: int) -> None:
    canvas.setFont(FONT_REGULAR, FOOTER_SIZE)
    canvas.drawCentredString(PAGE_WIDTH / 2, 12 * mm, page_label(number))


def _draw_paragraphs(canvas: PdfCanvas, texts: Iterable[str], style, top: float) -> float:
    """Draws paragraphs from `top` down, wrapped to the text width; returns where it ended."""
    width = PAGE_WIDTH - 2 * MARGIN_X
    y = top
    for text in texts:
        paragraph = Paragraph(escape(xml_safe(text)), style)
        _, height = paragraph.wrap(width, PAGE_HEIGHT)
        y -= height
        paragraph.drawOn(canvas, MARGIN_X, y)
        y -= style.fontSize / 2
    return y


def _cover(canvas: PdfCanvas, front: ComprovanteFront) -> None:
    styles = build_styles(12)
    header = front.header
    below = _draw_paragraphs(
        canvas, ["COMPROVANTE DE DOCUMENTOS"], styles.title, PAGE_HEIGHT - 70 * mm
    )
    _draw_paragraphs(
        canvas,
        [
            f"Docente: {header.professor_name}",
            f"Classe e nível atuais: {header.current_class}, nível {header.current_level}",
            f"Classe e nível pretendidos: {header.target_class}, nível {header.target_level}",
            f"Unidade: {header.unit_name}",
            f"Interstício: {format_interstice(header.interstice)}",
            f"Tabela de pontuação: {front.table_name}",
        ],
        styles.body_left,
        below - 12,
    )


def _toc_page(canvas: PdfCanvas, lines: Sequence[_Line], number: int) -> None:
    styles = build_styles(14)
    _draw_paragraphs(canvas, ["SUMÁRIO"], styles.title, PAGE_HEIGHT - 28 * mm)
    right = PAGE_WIDTH - MARGIN_X
    y = _FIRST_LINE_Y
    for line in lines:
        canvas.setFont(line.font, line.size)
        reserved = stringWidth(line.number, line.font, line.size) + _NUMBER_GAP
        room = right - MARGIN_X - line.indent - reserved
        canvas.drawString(MARGIN_X + line.indent, y, _fit(line.text, line.font, line.size, room))
        if line.number:
            canvas.drawRightString(right, y, line.number)
        y -= LINE_HEIGHT
    _footer(canvas, number)


def _separator(canvas: PdfCanvas, front: ComprovanteFront, page: PlanPage) -> None:
    styles = build_styles(18)
    title = _group_title(front, page.group_number or 0)
    _draw_paragraphs(canvas, [title], styles.title, PAGE_HEIGHT / 2 + 20)
    _footer(canvas, page.number)


def write_front_matter(plan: ComprovantePlan, front: ComprovanteFront, target: Path) -> None:
    """Writes the pages of the plan that are not originals, in order, to the PDF `target`.

    Page `n` of the file is the `n`-th generated page of the plan. Raises `ValueError` when the
    table of contents needs another number of pages than the plan reserved.
    """
    lines = toc_lines(plan, front)
    reserved = [p for p in plan.pages if p.kind is PageKind.SUMARIO]
    needed = -(-len(lines) // TOC_CAPACITY)
    if needed != len(reserved):
        raise ValueError(
            f"the table of contents needs {needed} pages and the plan has {len(reserved)}"
        )
    canvas = PdfCanvas(str(target), pagesize=A4)
    toc_index = 0
    for page in plan.pages:
        if page.kind is PageKind.ORIGINAL:
            continue
        if page.kind is PageKind.CAPA:
            _cover(canvas, front)
        elif page.kind is PageKind.SUMARIO:
            chunk = lines[toc_index * TOC_CAPACITY : (toc_index + 1) * TOC_CAPACITY]
            _toc_page(canvas, chunk, page.number)
            toc_index += 1
        else:
            _separator(canvas, front, page)
        canvas.showPage()
    canvas.save()
