"""The Tabela de Pontuação as PDF, drawn with reportlab (TAB-01, TAB-03 to TAB-06).

A4 landscape. The table has seven columns and a header row that repeats on every page; each group
is a band with the name of the table and the subtotal, empty groups included. The numbers come
from the `TableDocument` already written; nothing is summed here.
"""

from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.domain.rules.pt_format import format_interstice
from app.domain.rules.table_document import GroupBand, PitHours, TableDocument
from app.infrastructure.documents.pdf_styles import (
    FONT_REGULAR,
    NumberedCanvas,
    PdfStyles,
    build_styles,
)

FONT_SIZE = 8
MARGIN = 15 * mm
COLUMNS = (
    "Item",
    "Atividade",
    "Quantidade",
    "Pontuação unitária",
    "Total",
    "Comprovante",
    "Status",
)
_FIXED_WIDTHS = (38, None, 58, 68, 52, 82, 78)  # points; the activity column takes the rest
_GREY = colors.Color(0.9, 0.9, 0.9)
_LIGHT = colors.Color(0.96, 0.96, 0.96)
_LINE = colors.Color(0.4, 0.4, 0.4)


def _p(text: str, style) -> Paragraph:
    return Paragraph(escape(text), style)


def _widths(total: float) -> list[float]:
    fixed = sum(w for w in _FIXED_WIDTHS if w is not None)
    return [total - fixed if w is None else w for w in _FIXED_WIDTHS]


def _identification(document: TableDocument, styles: PdfStyles) -> list:
    header = document.header
    lines = (
        f"Docente: {header.professor_name}",
        f"Classe e nível atuais: {header.current_class}, nível {header.current_level}",
        f"Classe e nível pretendidos: {header.target_class}, nível {header.target_level}",
        f"Unidade: {header.unit_name}",
        f"Interstício: {format_interstice(header.interstice)}",
        f"Tabela de pontuação: {document.table_name}",
        f"Referência normativa: {document.norm_reference}",
    )
    return [
        Paragraph("TABELA DE PONTUAÇÃO", styles.title),
        *(_p(line, styles.body_left) for line in lines),
        Spacer(1, 8),
    ]


def _main_table(document: TableDocument, styles: PdfStyles, width: float) -> Table:
    rows: list[list] = [[_p(name, styles.cell_header) for name in COLUMNS]]
    commands: list[tuple] = [
        ("FONTNAME", (0, 0), (-1, -1), FONT_REGULAR),  # empty cells are drawn with it too
        ("GRID", (0, 0), (-1, -1), 0.25, _LINE),
        ("BACKGROUND", (0, 0), (-1, 0), _GREY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ]

    def band_row(band: GroupBand) -> None:
        index = len(rows)
        rows.append(
            [_p(f"{band.numeral}. {band.name}", styles.band), "", "", "",
             _p(f"Subtotal: {band.subtotal}", styles.band), "", ""]
        )  # fmt: skip
        commands.extend(
            [
                ("SPAN", (0, index), (3, index)),
                ("SPAN", (4, index), (6, index)),
                ("BACKGROUND", (0, index), (-1, index), _LIGHT),
            ]
        )
        if band.rows:  # a band never ends a page alone
            commands.append(("NOSPLIT", (0, index), (-1, index + 1)))

    for band in document.bands:
        band_row(band)
        for row in band.rows:
            cells = (row.item, row.title, row.quantity, row.unit_points, row.points,
                     row.comprovante, row.status)  # fmt: skip
            rows.append([_p(cell, styles.cell) for cell in cells])

    index = len(rows)
    rows.append([_p(f"Pontuação geral: {document.total}", styles.band), "", "", "", "", "", ""])
    commands.extend(
        [("SPAN", (0, index), (-1, index)), ("BACKGROUND", (0, index), (-1, index), _GREY)]
    )
    table = Table(rows, colWidths=_widths(width), repeatRows=1)
    table.setStyle(TableStyle(commands))
    return table


def _counters(document: TableDocument, styles: PdfStyles) -> Paragraph:
    c = document.counters
    parts = (
        f"Atividades: {c.activities}",
        f"Com comprovante: {c.with_evidence}",
        f"Pendentes: {c.pending}",
        f"Não pontuadas: {c.not_scored}",
        f"Com divergências: {c.with_alerts}",
    )
    return _p("   |   ".join(parts), styles.body_left)


def _pit_section(pit: PitHours, styles: PdfStyles) -> list:
    rows = [[_p("Período letivo", styles.cell_header), _p("Horas de PIT", styles.cell_header)]]
    rows += [[_p(p.label, styles.cell), _p(p.hours, styles.cell)] for p in pit.periods]
    rows.append([_p("Total em horas", styles.band), _p(pit.total, styles.band)])
    table = Table(rows, colWidths=[180, 90], hAlign="LEFT", repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), FONT_REGULAR),
                ("GRID", (0, 0), (-1, -1), 0.25, _LINE),
                ("BACKGROUND", (0, 0), (-1, 0), _GREY),
                ("BACKGROUND", (0, -1), (-1, -1), _GREY),
            ]
        )
    )
    return [
        Spacer(1, 10),
        KeepTogether(
            [
                _p("Horas de PIT por semestre (Grupo I, fora do total de pontos)", styles.heading),
                table,
            ]
        ),
    ]


def _alerts(document: TableDocument, styles: PdfStyles) -> list:
    if not document.alerts:
        return []
    items = [
        _p(f"{a.subject}: {a.message}" if a.subject else a.message, styles.body_left)
        for a in document.alerts
    ]
    return [Spacer(1, 10), _p("Alertas", styles.heading), *items]


def write_table_pdf(document: TableDocument, target: Path) -> None:
    """Writes the PDF to `target` (a path, never a stream)."""
    styles = build_styles(FONT_SIZE)
    page = landscape(A4)
    template = SimpleDocTemplate(
        str(target),
        pagesize=page,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=20 * mm,
        title="Tabela de Pontuação",
    )
    width = page[0] - 2 * MARGIN
    story = [
        *_identification(document, styles),
        _main_table(document, styles, width),
        Spacer(1, 8),
        _counters(document, styles),
        *(_pit_section(document.pit_hours, styles) if document.pit_hours else []),
        *_alerts(document, styles),
    ]
    template.build(story, canvasmaker=NumberedCanvas)
