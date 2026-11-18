"""Content of the scoring table document (TAB-02 to TAB-06): header, group bands, rows, totals,
counters, PIT hours and alerts.

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
from app.domain.rules.process_verification import Alert
from app.domain.rules.pt_format import format_decimal, format_period
from app.domain.rules.scoring_alerts import NotScoredReason
from app.domain.rules.scoring_engine import (
    Counters,
    RowStatus,
    ScoringResult,
    ScoringRow,
    is_pit_criterion,
)

NO_VOUCHER = "sem comprovante"
EMPTY_CELL = "—"
_ROMAN = {1: "I", 2: "II", 3: "III", 4: "IV", 5: "V", 6: "VI", 7: "VII", 8: "VIII"}
_STATUS_TEXT = {
    RowStatus.PONTUADA: "Pontuada",
    RowStatus.POTENCIAL: "Potencial",
    RowStatus.NAO_PONTUADA: "Não pontuada",
}
# The words the scoring screen shows for each reason a row is not scored (`REASON_LABELS`).
_REASON_TEXT = {
    NotScoredReason.FORA_DO_INTERSTICIO: "Fora do interstício",
    NotScoredReason.DUPLICIDADE: "Duplicidade",
    NotScoredReason.SEM_ENQUADRAMENTO: "Sem enquadramento na tabela",
    NotScoredReason.GRUPO_NAO_CONTA: "Grupo não conta no total",
    NotScoredReason.SEM_TABELA: "Sem tabela escolhida",
    NotScoredReason.REJEITADA: "Rejeitada",
    NotScoredReason.CARGA_HORARIA_INSUFICIENTE: "Carga horária abaixo do mínimo do item",
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
class PitPeriodHours:
    label: str
    hours: str


@dataclass(frozen=True)
class PitHours:
    """Group I offers measured in hours: a section apart, never added to the points (TAB-05)."""

    periods: tuple[PitPeriodHours, ...]
    total: str


@dataclass(frozen=True)
class TableAlert:
    """An alert or a reason of the scoring, with the words of the screen.

    `subject` is the title of the activity it concerns; none for the alerts of the process.
    """

    code: str
    message: str
    subject: str | None = None


@dataclass(frozen=True)
class TableDocument:
    header: TableHeader
    table_name: str
    norm_reference: str
    bands: tuple[GroupBand, ...]
    total: str
    counters: Counters
    pit_hours: PitHours | None
    alerts: tuple[TableAlert, ...]


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


def _pit_hours(version: ScoringTableVersion, result: ScoringResult) -> PitHours | None:
    """The section exists only when the version measures group I in PIT hours."""
    has_pit = any(is_pit_criterion(version, c) for g in version.groups for c in g.criteria)
    if not has_pit:
        return None
    periods = tuple(
        PitPeriodHours(format_period(period), two_places(hours))
        for period, hours in result.group1_hours_by_period.items()
    )
    return PitHours(periods, two_places(result.group1_total_hours))


def _alerts(
    result: ScoringResult, titles: Mapping[UUID, str], process_alerts: Sequence[Alert]
) -> tuple[TableAlert, ...]:
    """Alerts and reasons of the listed activities, then the limits of criteria and groups.

    A limit on one activity is already one of its row alerts, so it is not listed again.
    """
    found: list[TableAlert] = []
    for row in result.rows:
        if row.activity_id not in titles:
            continue
        subject = titles[row.activity_id]
        found += [TableAlert(a.code.value, a.message, subject) for a in row.alerts]
        found += [TableAlert(r.value, _REASON_TEXT[r], subject) for r in row.reasons]
    for adjustment in result.limit_adjustments:
        if adjustment.scope != "ATIVIDADE":
            found.append(TableAlert(adjustment.alert.code.value, adjustment.alert.message))
    found += [TableAlert(a.code.value, a.message) for a in process_alerts]
    return tuple(found)


def build_table_document(
    header: TableHeader,
    version: ScoringTableVersion,
    result: ScoringResult,
    activities: Sequence[Activity],
    comprovante_numbers: Mapping[UUID, int],
    process_alerts: Sequence[Alert] = (),
) -> TableDocument:
    """`activities` are the ones that go in the document; `comprovante_numbers` come from the plan.

    A group that counts in the total is a band, empty ones included. A group outside the total
    (group I in hours) has no band; its hours are the `pit_hours` section. `process_alerts` are
    the alerts of the process the screen shows beside the result.
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
        total=two_places(result.total),
        counters=result.counters,
        pit_hours=_pit_hours(version, result),
        alerts=_alerts(result, titles, process_alerts),
    )
