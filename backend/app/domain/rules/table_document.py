"""Content of the scoring table document: header, group bands and rows (TAB-02, TAB-03).

Pure function of the scoring result: the document and the screen cannot disagree because the
subtotals and the total are the engine's, never summed again here. The writers (DOCX, PDF) only
draw this model.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from app.domain.entities.activity import Activity
from app.domain.entities.scoring import ScoringTableVersion
from app.domain.rules.interstice import Interstice
from app.domain.rules.pt_format import format_decimal
from app.domain.rules.scoring_engine import RowStatus, ScoringResult, ScoringRow, is_pit_criterion

NO_VOUCHER = "sem comprovante"
EMPTY_CELL = "—"
_ROMAN = {1: "I", 2: "II", 3: "III", 4: "IV", 5: "V", 6: "VI", 7: "VII", 8: "VIII"}
_STATUS_TEXT = {
    RowStatus.PONTUADA: "Pontuada",
    RowStatus.POTENCIAL: "Potencial",
    RowStatus.NAO_PONTUADA: "Não pontuada",
}
_CENTS = Decimal("0.01")


@dataclass(frozen=True)
class TableHeader:
    """Who and what the document is about; the writers format the interstice."""

    professor_name: str
    current_class: str
    current_level: int
    target_class: str
    target_level: int
    unit_name: str
    interstice: Interstice


@dataclass(frozen=True)
class TableRow:
    """One activity: the seven columns of the table, already written."""

    activity_id: UUID
    item: str
    title: str
    quantity: str
    unit_points: str
    points: str
    comprovante: str
    status: str


@dataclass(frozen=True)
class GroupBand:
    """A group as a band with the name of the table and its subtotal, even when empty."""

    group_number: int
    numeral: str
    name: str
    subtotal: str
    rows: tuple[TableRow, ...]


@dataclass(frozen=True)
class TableDocument:
    header: TableHeader
    table_name: str
    norm_reference: str
    bands: tuple[GroupBand, ...]


def roman(group_number: int) -> str:
    return _ROMAN.get(group_number, str(group_number))


def two_places(value: Decimal) -> str:
    """The screen shows every figure with two places: `52.00` -> `52,00`."""
    return format_decimal(value.quantize(_CENTS))


def _cell(value: Decimal | None) -> str:
    return EMPTY_CELL if value is None else two_places(value)


def _table_row(row: ScoringRow, title: str, comprovante_numbers: Mapping[UUID, int]) -> TableRow:
    number = comprovante_numbers.get(row.activity_id)
    return TableRow(
        activity_id=row.activity_id,
        item=f"{roman(row.group_number)}.{row.item_number}",
        title=title,
        quantity=_cell(row.effective_quantity),
        unit_points=_cell(row.unit_points),
        points=two_places(row.points),
        comprovante=NO_VOUCHER if number is None else str(number),
        status=_STATUS_TEXT[row.status],
    )


def _band_rows(
    group_number: int,
    version: ScoringTableVersion,
    result: ScoringResult,
    titles: Mapping[UUID, str],
    comprovante_numbers: Mapping[UUID, int],
) -> tuple[TableRow, ...]:
    """Rows of the listed activities in the group, by item and then in the given order."""
    found = [
        row for row in result.rows if row.activity_id in titles and row.group_number == group_number
    ]
    found = [row for row in found if not _is_pit(version, row)]
    found.sort(key=lambda row: row.item_number or 0)
    return tuple(_table_row(r, titles[r.activity_id], comprovante_numbers) for r in found)


def _is_pit(version: ScoringTableVersion, row: ScoringRow) -> bool:
    """Group I weekly-load offers: their hours go to the separate PIT section, not to a band."""
    criterion = version.get_criterion(row.group_number, row.item_number)
    return criterion is not None and is_pit_criterion(version, criterion)


def build_table_document(
    header: TableHeader,
    version: ScoringTableVersion,
    result: ScoringResult,
    activities: Sequence[Activity],
    comprovante_numbers: Mapping[UUID, int],
) -> TableDocument:
    """`activities` are the ones that go in the document; `comprovante_numbers` come from the plan.

    A group that counts in the total is a band, empty ones included. A group outside the total
    (group I in hours) has no band.
    """
    titles = {a.id: a.title for a in activities}
    bands = tuple(
        GroupBand(
            group_number=group.number,
            numeral=roman(group.number),
            name=group.name,
            subtotal=two_places(result.group_subtotals[group.number]),
            rows=_band_rows(group.number, version, result, titles, comprovante_numbers),
        )
        for group in sorted(version.groups, key=lambda g: g.number)
        if group.counts_in_total
    )
    return TableDocument(
        header=header,
        table_name=version.name,
        norm_reference=version.norm_reference,
        bands=bands,
    )
