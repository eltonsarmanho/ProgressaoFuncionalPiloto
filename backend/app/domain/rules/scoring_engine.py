"""Deterministic scoring engine (CALC-01, CALC-07..CALC-13, VERIF-08).

Pure function of (table version, activities, interstice). Evaluation order per activity:
criterion exists -> status REJEITADA -> period -> group counts in total -> duplicate ->
points -> limits (criterion cap, then group cap, only on activities that count).
Per-activity points stay uncapped; caps apply to the summed subtotals and are reported in
`limit_adjustments` with the points before and after.

Group I of the official table is reported in PIT hours, not points (PIT-01, PIT-02): a
CARGA_SEMANAL criterion of group I in a group that does not count in the total yields a row
with `points = 0` and `pit_hours`, summed per academic period in `group1_hours_by_period`.
Tables whose group I counts in the total keep the points calculation (processes that chose
them are unchanged).
"""

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum
from uuid import UUID

from app.domain.entities.activity import Activity, ActivityStatus
from app.domain.entities.scoring import ScoringCriterion, ScoringMode, ScoringTableVersion
from app.domain.rules.interstice import Interstice
from app.domain.rules.process_verification import Alert, Severity
from app.domain.rules.scoring_alerts import NotScoredReason, ScoringAlertCode
from app.domain.rules.scoring_duplicates import find_duplicates
from app.domain.rules.scoring_periods import PeriodState, evaluate_period
from app.domain.rules.scoring_points import criterion_points

ZERO = Decimal(0)
GROUPS = range(1, 9)


class RowStatus(StrEnum):
    PONTUADA = "PONTUADA"
    POTENCIAL = "POTENCIAL"
    NAO_PONTUADA = "NAO_PONTUADA"


@dataclass(frozen=True)
class ScoringRow:
    activity_id: UUID
    group_number: int | None
    item_number: int | None
    unit_points: Decimal | None
    effective_quantity: Decimal | None
    formula_text: str
    points: Decimal
    status: RowStatus
    reasons: tuple[NotScoredReason, ...] = ()
    alerts: tuple[Alert, ...] = ()
    evidence_count: int = 0  # documents linked to the activity (VINC-04)
    pit_hours: Decimal | None = None  # group I rows only: PIT hours of the offer


@dataclass(frozen=True)
class LimitAdjustment:
    scope: str  # "ATIVIDADE", "CRITERIO" or "GRUPO"
    group_number: int
    item_number: int | None
    before: Decimal
    after: Decimal
    alert: Alert
    activity_id: UUID | None = None


@dataclass(frozen=True)
class Counters:
    activities: int
    with_evidence: int
    pending: int
    not_scored: int
    with_alerts: int


@dataclass(frozen=True)
class ScoringResult:
    rows: tuple[ScoringRow, ...]
    group_subtotals: dict[int, Decimal]
    total: Decimal
    potential_total: Decimal
    group1_percent: Decimal | None
    counters: Counters
    limit_adjustments: tuple[LimitAdjustment, ...]
    group1_hours_by_period: dict[str, Decimal] = field(default_factory=dict)
    group1_total_hours: Decimal = ZERO
    # `potential_total` split (REAL-08): activities with a date or period against those without
    potential_dated: Decimal = ZERO
    potential_undated: Decimal = ZERO


def is_pit_criterion(version: ScoringTableVersion, criterion: ScoringCriterion) -> bool:
    """Group I weekly-load criterion of a table whose group I is outside the total."""
    group = version.get_group(criterion.group_number)
    return (
        criterion.group_number == 1
        and criterion.mode is ScoringMode.CARGA_SEMANAL
        and group is not None
        and not group.counts_in_total
    )


def _row_alert(code: ScoringAlertCode, message: str, version: ScoringTableVersion) -> Alert:
    return Alert(code, Severity.ALERTA, message, version.norm_reference)


def _limit_alert(label: str, before: Decimal, after: Decimal, version) -> Alert:
    message = f"Limite aplicado em {label}: {before} pontos reduzidos para {after}."
    return _row_alert(ScoringAlertCode.LIMITE_APLICADO, message, version)


def has_evidence(activity: Activity, evidence_count: int) -> bool:
    """A linked document or a non-empty evidence note proves the activity (VINC-04)."""
    return evidence_count > 0 or bool((activity.evidence_note or "").strip())


def _not_scored(activity: Activity, reason: NotScoredReason, evidence_count: int) -> ScoringRow:
    return ScoringRow(
        activity_id=activity.id,
        group_number=activity.group_number,
        item_number=activity.item_number,
        unit_points=None,
        effective_quantity=None,
        formula_text="",
        points=ZERO,
        status=RowStatus.NAO_PONTUADA,
        reasons=(reason,),
        evidence_count=evidence_count,
    )


def _period_alerts(state: PeriodState, version: ScoringTableVersion) -> list[Alert]:
    if state is PeriodState.PARCIAL:
        message = (
            "O período da atividade ultrapassa o interstício; pontuada com a quantidade "
            "informada, sem proporcionalizar."
        )
        return [_row_alert(ScoringAlertCode.INTERSTICIO_PARCIAL, message, version)]
    if state is PeriodState.SEM_DATA:
        message = "A atividade não tem data nem período; pontuada sem verificação do interstício."
        return [_row_alert(ScoringAlertCode.DATA_AUSENTE, message, version)]
    return []


def _evaluate(
    activity: Activity,
    version: ScoringTableVersion,
    interstice: Interstice,
    duplicates: set[UUID],
    limit_adjustments: list[LimitAdjustment],
    evidence_count: int,
) -> ScoringRow:
    criterion = None
    if activity.group_number is not None and activity.item_number is not None:
        criterion = version.get_criterion(activity.group_number, activity.item_number)
    if criterion is None:
        return _not_scored(activity, NotScoredReason.SEM_ENQUADRAMENTO, evidence_count)
    if activity.status is ActivityStatus.REJEITADA:
        return _not_scored(activity, NotScoredReason.REJEITADA, evidence_count)

    state = evaluate_period(activity, interstice)
    if state is PeriodState.FORA:
        return _not_scored(activity, NotScoredReason.FORA_DO_INTERSTICIO, evidence_count)

    group = version.get_group(criterion.group_number)
    pit = is_pit_criterion(version, criterion)
    if group is not None and not group.counts_in_total and not pit:
        return _not_scored(activity, NotScoredReason.GRUPO_NAO_CONTA, evidence_count)
    if activity.id in duplicates:
        return _not_scored(activity, NotScoredReason.DUPLICIDADE, evidence_count)

    missing_hours = False
    if criterion.min_hours is not None:
        if activity.hours is None:
            missing_hours = True
        elif activity.hours < criterion.min_hours:
            return _not_scored(activity, NotScoredReason.CARGA_HORARIA_INSUFICIENTE, evidence_count)

    # PIT hours come from the weekly load only; informed points never replace them
    scored_activity = replace(activity, points_override=None) if pit else activity
    result = criterion_points(criterion, scored_activity)
    alerts = _period_alerts(state, version)
    if missing_hours:
        message = (
            f"O item exige carga horária mínima de {criterion.min_hours:f} h e as horas não "
            "foram informadas; pontuada, a revisão humana confere a carga."
        )
        alerts.append(_row_alert(ScoringAlertCode.CARGA_HORARIA_NAO_INFORMADA, message, version))
    if not has_evidence(activity, evidence_count):
        message = "A atividade não tem documento vinculado nem nota de comprovante."
        alerts.append(_row_alert(ScoringAlertCode.SEM_COMPROVANTE, message, version))
    if result.overridden:
        message = "Pontos informados manualmente substituem o cálculo da carga semanal."
        alerts.append(_row_alert(ScoringAlertCode.PONTOS_AJUSTADOS_MANUALMENTE, message, version))
    if result.limited_from is not None:
        label = f"{criterion.group_number}.{criterion.item_number}"
        alert = _limit_alert(
            f"atividade do item {label}", result.limited_from, result.points, version
        )
        alerts.append(alert)
        limit_adjustments.append(
            LimitAdjustment(
                "ATIVIDADE",
                criterion.group_number,
                criterion.item_number,
                result.limited_from,
                result.points,
                alert,
                activity.id,
            )
        )

    scored = activity.status is ActivityStatus.VALIDADA
    if pit:
        return ScoringRow(
            activity_id=activity.id,
            group_number=activity.group_number,
            item_number=activity.item_number,
            unit_points=criterion.unit_points,
            effective_quantity=result.effective_quantity,
            formula_text=result.formula_text,
            points=ZERO,
            status=RowStatus.PONTUADA if scored else RowStatus.POTENCIAL,
            alerts=tuple(alerts),
            evidence_count=evidence_count,
            pit_hours=result.points,
        )
    return ScoringRow(
        activity_id=activity.id,
        group_number=activity.group_number,
        item_number=activity.item_number,
        unit_points=criterion.unit_points,
        effective_quantity=result.effective_quantity,
        formula_text=result.formula_text,
        points=result.points,
        status=RowStatus.PONTUADA if scored else RowStatus.POTENCIAL,
        alerts=tuple(alerts),
        evidence_count=evidence_count,
    )


def _subtotals(
    version: ScoringTableVersion, rows: Sequence[ScoringRow], adjustments: list[LimitAdjustment]
) -> dict[int, Decimal]:
    per_criterion: dict[tuple[int, int], Decimal] = defaultdict(lambda: ZERO)
    for row in rows:
        if row.status is RowStatus.PONTUADA:
            per_criterion[(row.group_number, row.item_number)] += row.points

    subtotals = {number: ZERO for number in GROUPS}
    for group in version.groups:
        group_sum = ZERO
        for (group_number, item_number), summed in sorted(per_criterion.items()):
            if group_number != group.number:
                continue
            criterion = version.get_criterion(group_number, item_number)
            if criterion.max_points is not None and summed > criterion.max_points:
                label = f"critério {group_number}.{item_number}"
                alert = _limit_alert(label, summed, criterion.max_points, version)
                adjustments.append(
                    LimitAdjustment(
                        "CRITERIO", group_number, item_number, summed, criterion.max_points, alert
                    )
                )
                summed = criterion.max_points
            group_sum += summed
        if group.max_points is not None and group_sum > group.max_points:
            alert = _limit_alert(f"grupo {group.number}", group_sum, group.max_points, version)
            adjustments.append(
                LimitAdjustment("GRUPO", group.number, None, group_sum, group.max_points, alert)
            )
            group_sum = group.max_points
        subtotals[group.number] = group_sum
    return subtotals


def _pit_hours_by_period(
    rows: Sequence[ScoringRow], activities: Sequence[Activity]
) -> tuple[dict[str, Decimal], Decimal]:
    """Hours of validated group I offers, per academic period (sorted) and in total.

    An offer without an academic period counts in the total only.
    """
    periods = {a.id: a.academic_period for a in activities}
    by_period: dict[str, Decimal] = defaultdict(lambda: ZERO)
    total = ZERO
    for row in rows:
        if row.status is not RowStatus.PONTUADA or row.pit_hours is None:
            continue
        total += row.pit_hours
        period = periods[row.activity_id]
        if period is not None:
            by_period[period] += row.pit_hours
    return dict(sorted(by_period.items())), total


def _is_undated_potential(row: ScoringRow) -> bool:
    """A potential row whose activity has no date nor period (it carries DATA_AUSENTE)."""
    return row.status is RowStatus.POTENCIAL and any(
        alert.code is ScoringAlertCode.DATA_AUSENTE for alert in row.alerts
    )


def calculate(
    version: ScoringTableVersion,
    activities: Sequence[Activity],
    interstice: Interstice,
    evidence_counts: Mapping[UUID, int] | None = None,
) -> ScoringResult:
    """`evidence_counts` maps an activity id to its linked documents; absent means none."""
    counts = evidence_counts or {}
    duplicates = find_duplicates(activities)
    adjustments: list[LimitAdjustment] = []
    rows = tuple(
        _evaluate(a, version, interstice, duplicates, adjustments, counts.get(a.id, 0))
        for a in activities
    )

    subtotals = _subtotals(version, rows, adjustments)
    total = sum(subtotals.values(), ZERO)
    potential = sum((r.points for r in rows if r.status is RowStatus.POTENCIAL), ZERO)
    undated = sum((r.points for r in rows if _is_undated_potential(r)), ZERO)
    percent = None
    if total > 0:
        percent = (subtotals[1] * 100 / total).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    counters = Counters(
        activities=len(activities),
        with_evidence=sum(1 for a in activities if has_evidence(a, counts.get(a.id, 0))),
        pending=sum(1 for a in activities if a.status is ActivityStatus.AGUARDANDO_REVISAO),
        not_scored=sum(1 for r in rows if r.status is RowStatus.NAO_PONTUADA),
        with_alerts=sum(1 for r in rows if r.alerts),
    )
    hours_by_period, hours_total = _pit_hours_by_period(rows, activities)
    return ScoringResult(
        rows,
        subtotals,
        total,
        potential,
        percent,
        counters,
        tuple(adjustments),
        hours_by_period,
        hours_total,
        potential - undated,
        undated,
    )
