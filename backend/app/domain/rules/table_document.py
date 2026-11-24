"""Content of the scoring table document (TAB-02 to TAB-06, GTAB-01 to GTAB-08): header, group
bands, rows, totals, counters, PIT hours and alerts.

Pure function of the scoring result: the document and the screen cannot disagree because the
subtotals and the total are the engine's, never summed again here. The writers (DOCX, PDF) only
draw this model.
"""

import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from app.domain.entities.activity import Activity
from app.domain.entities.scoring import ScoringTableVersion, is_group1_load_criterion
from app.domain.rules.interstice import Interstice
from app.domain.rules.process_verification import Alert
from app.domain.rules.pt_format import format_decimal, format_period
from app.domain.rules.scoring_alerts import NotScoredReason, ScoringAlertCode
from app.domain.rules.scoring_engine import (
    Counters,
    ScoringResult,
    ScoringRow,
)

MAX_TITLE_CHARS = 400  # a table row cannot be taller than a page: a longer title is cut with "…"
EMPTY_CELL = "—"
_ROMAN = {1: "I", 2: "II", 3: "III", 4: "IV", 5: "V", 6: "VI", 7: "VII", 8: "VIII"}
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
GROUP_ONE = 1
GROUP_ONE_UNIT_POINTS = Decimal("1")  # one point per PIT hour (D7): `points == pit_hours`


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
    """One activity: the five columns of the table, already written."""

    activity_id: UUID
    item: str
    title: str
    quantity: str
    unit_points: str
    points: str


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
    """Group I offers summed in hours per term. `outside_total` is true when the table version
    keeps the group out of the total, so the hours are not points (TAB-05, GTAB-06, GTAB-07)."""

    periods: tuple[PitPeriodHours, ...]
    total: str
    outside_total: bool = False


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


def _shown_title(title: str) -> str:
    """The title as the Tabela shows it: whole up to `MAX_TITLE_CHARS`, else cut and ended by "…",
    exactly `MAX_TITLE_CHARS` characters long. The activity keeps its full title."""
    if len(title) <= MAX_TITLE_CHARS:
        return title
    return title[: MAX_TITLE_CHARS - 1] + "…"


def _table_row(row: ScoringRow, title: str, offer: bool = False) -> TableRow:
    """A group I offer row shows the PIT hours as quantity and one point per hour (D7)."""
    hours = row.pit_hours
    return TableRow(
        activity_id=row.activity_id,
        item=f"{roman(row.group_number)}.{row.item_number}",
        title=title,
        quantity=_cell(hours if offer else row.effective_quantity),
        unit_points=two_places(GROUP_ONE_UNIT_POINTS) if offer else _cell(row.unit_points),
        points=two_places(row.points),
    )


def _term_key(period: str | None, title: str) -> tuple[bool, str, str]:
    """Group I order: by academic term (an offer without one last), then by title ignoring case
    and accents."""
    plain = unicodedata.normalize("NFKD", title.casefold())
    letters = "".join(c for c in plain if not unicodedata.combining(c))
    return (period is None, period or "", letters)


def _group_one_rows(
    found: list[ScoringRow],
    titles: Mapping[UUID, str],
    terms: Mapping[UUID, str | None],
) -> tuple[TableRow, ...]:
    """One row per offer: the title cut as the others, then the term in words (GTAB-02)."""
    found.sort(key=lambda r: _term_key(terms[r.activity_id], titles[r.activity_id]))
    rows = []
    for row in found:
        term = terms[row.activity_id]
        title = titles[row.activity_id]
        shown = title if term is None else f"{title} ({format_period(term)})"
        rows.append(_table_row(row, shown, offer=row.pit_hours is not None))
    return tuple(rows)


def _band_rows(
    group_number: int,
    result: ScoringResult,
    titles: Mapping[UUID, str],
    terms: Mapping[UUID, str | None],
) -> tuple[TableRow, ...]:
    """Rows of the listed activities in the group, by item and then in the given order; the
    group I offers by term and title instead."""
    found = [
        row
        for row in result.rows
        if row.activity_id in titles and row.group_number == group_number and not row.outside_total
    ]
    if group_number == GROUP_ONE:
        return _group_one_rows(found, titles, terms)
    found.sort(key=lambda row: row.item_number or 0)
    return tuple(_table_row(r, titles[r.activity_id]) for r in found)


def _pit_hours(version: ScoringTableVersion, result: ScoringResult) -> PitHours | None:
    """The section exists whenever the version measures group I by weekly load (PIT hours)."""
    load = [c for g in version.groups for c in g.criteria if is_group1_load_criterion(c)]
    if not load:
        return None
    group = version.get_group(GROUP_ONE)
    periods = tuple(
        PitPeriodHours(format_period(period), two_places(hours))
        for period, hours in result.group1_hours_by_period.items()
    )
    return PitHours(
        periods,
        two_places(result.group1_total_hours),
        outside_total=group is not None and not group.counts_in_total,
    )


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
        found += [
            TableAlert(a.code.value, a.message, subject)
            for a in row.alerts
            if a.code is not ScoringAlertCode.SEM_COMPROVANTE  # GTAB-08: no voucher in the table
        ]
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
    process_alerts: Sequence[Alert] = (),
) -> TableDocument:
    """`activities` are the ones that go in the document.

    A group that counts in the total is a band, empty ones included, group I among them when the
    version counts it (one row per offer). A group outside the total (group I of the old version)
    has no band; its hours are the `pit_hours` section. `process_alerts` are
    the alerts of the process the screen shows beside the result.
    """
    titles = {a.id: _shown_title(a.title) for a in activities}
    terms = {a.id: a.academic_period for a in activities}
    bands = tuple(
        GroupBand(
            group_number=group.number,
            numeral=roman(group.number),
            name=group.name,
            subtotal=two_places(result.group_subtotals[group.number]),
            rows=_band_rows(group.number, result, titles, terms),
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
