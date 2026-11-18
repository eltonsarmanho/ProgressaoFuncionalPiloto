"""Deterministic scoring engine (CALC-01, CALC-07..CALC-13, VERIF-08).

Pure function of (table version, activities, interstice). Evaluation order per activity:
criterion exists -> status REJEITADA -> period -> group counts in total -> duplicate ->
points -> limits (criterion cap, then group cap, only on activities that count).
Per-activity points stay uncapped; caps apply to the summed subtotals and are reported in
`limit_adjustments` with the points before and after.
"""

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum
from uuid import UUID

from app.domain.entities.activity import Activity, ActivityStatus
from app.domain.entities.scoring import ScoringTableVersion
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


def _row_alert(code: ScoringAlertCode, message: str, version: ScoringTableVersion) -> Alert:
    return Alert(code, Severity.ALERTA, message, version.norm_reference)


def _limit_alert(label: str, before: Decimal, after: Decimal, version) -> Alert:
    message = f"Limite aplicado em {label}: {before} pontos reduzidos para {after}."
    return _row_alert(ScoringAlertCode.LIMITE_APLICADO, message, version)


def _not_scored(activity: Activity, reason: NotScoredReason) -> ScoringRow:
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
) -> ScoringRow:
    criterion = None
    if activity.group_number is not None and activity.item_number is not None:
        criterion = version.get_criterion(activity.group_number, activity.item_number)
    if criterion is None:
        return _not_scored(activity, NotScoredReason.SEM_ENQUADRAMENTO)
    if activity.status is ActivityStatus.REJEITADA:
        return _not_scored(activity, NotScoredReason.REJEITADA)

    state = evaluate_period(activity, interstice)
    if state is PeriodState.FORA:
        return _not_scored(activity, NotScoredReason.FORA_DO_INTERSTICIO)

    group = version.get_group(criterion.group_number)
    if group is not None and not group.counts_in_total:
        return _not_scored(activity, NotScoredReason.GRUPO_NAO_CONTA)
    if activity.id in duplicates:
        return _not_scored(activity, NotScoredReason.DUPLICIDADE)

    result = criterion_points(criterion, activity)
    alerts = _period_alerts(state, version)
    if not (activity.evidence_note or "").strip():
        message = "A atividade não tem nota de comprovante."
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


def calculate(
    version: ScoringTableVersion, activities: Sequence[Activity], interstice: Interstice
) -> ScoringResult:
    duplicates = find_duplicates(activities)
    adjustments: list[LimitAdjustment] = []
    rows = tuple(_evaluate(a, version, interstice, duplicates, adjustments) for a in activities)

    subtotals = _subtotals(version, rows, adjustments)
    total = sum(subtotals.values(), ZERO)
    potential = sum((r.points for r in rows if r.status is RowStatus.POTENCIAL), ZERO)
    percent = None
    if total > 0:
        percent = (subtotals[1] * 100 / total).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    counters = Counters(
        activities=len(activities),
        with_evidence=sum(1 for a in activities if (a.evidence_note or "").strip()),
        pending=sum(1 for a in activities if a.status is ActivityStatus.AGUARDANDO_REVISAO),
        not_scored=sum(1 for r in rows if r.status is RowStatus.NAO_PONTUADA),
        with_alerts=sum(1 for r in rows if r.alerts),
    )
    return ScoringResult(rows, subtotals, total, potential, percent, counters, tuple(adjustments))
