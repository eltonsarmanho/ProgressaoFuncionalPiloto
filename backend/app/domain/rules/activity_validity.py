"""Whether an activity is valid, and why not (VAL-06, SEC-02, SEC-06, SEC-07, SEG-01).

One pure decision for the scoring engine, the Etapa 3 list and the generated documents. A not
valid activity is out of the score, the Tabela, the Relatório and the Comprovante, and the
screen tells the reason. An activity with no category stays valid and is flagged: it cannot
be validated until the person picks the category.

Order of the reasons, the one of the engine: rejected; date outside the interstice; no
category (valid, `needs_category`); a group outside the total that is not PIT; residual
duplicate; hours below the minimum of the item. With no table chosen only what does not
depend on it is judged: rejected, the date taken as a day, and the category.
"""

from collections.abc import Mapping, Set
from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum
from typing import Any
from uuid import UUID

from app.domain.entities.activity import Activity, ActivityStatus
from app.domain.entities.scoring import ScoringTableVersion, is_pit_criterion
from app.domain.rules.interstice import Interstice
from app.domain.rules.scoring_periods import PeriodState, evaluate_period, is_yearly_unit


class ValidityState(StrEnum):
    VALIDA = "VALIDA"
    NAO_VALIDA = "NAO_VALIDA"


class InvalidReason(StrEnum):
    REJEITADA = "REJEITADA"
    FORA_DO_INTERSTICIO = "FORA_DO_INTERSTICIO"
    CARGA_HORARIA_INSUFICIENTE = "CARGA_HORARIA_INSUFICIENTE"
    GRUPO_NAO_CONTA = "GRUPO_NAO_CONTA"
    DUPLICIDADE = "DUPLICIDADE"


@dataclass(frozen=True)
class Validity:
    """`params` carries what the reason needs to be written: the date or the period and the
    interstice (FORA_DO_INTERSTICIO), the hours and the minimum (CARGA_HORARIA_INSUFICIENTE)."""

    state: ValidityState
    reason: InvalidReason | None = None
    needs_category: bool = False
    params: Mapping[str, Any] = field(default_factory=dict)

    @property
    def is_valid(self) -> bool:
        return self.state is ValidityState.VALIDA


def _invalid(reason: InvalidReason, params: Mapping[str, Any] | None = None) -> Validity:
    return Validity(ValidityState.NAO_VALIDA, reason, False, params or {})


def _outside_params(activity: Activity, interstice: Interstice) -> dict[str, date | str | None]:
    """What the reason is written from: the date, the period of dates, or (a group I offer with
    neither) its academic period, always with the interstice."""
    when: dict[str, date | str | None]
    if activity.event_date is not None:
        when = {"event_date": activity.event_date}
    elif activity.period_start is not None or activity.period_end is not None:
        when = {"period_start": activity.period_start, "period_end": activity.period_end}
    else:
        when = {"academic_period": activity.academic_period}
    return {**when, "interstice_start": interstice.start, "interstice_end": interstice.end}


def classify_activity(
    activity: Activity,
    version: ScoringTableVersion | None,
    interstice: Interstice,
    duplicates: Set[UUID],
) -> Validity:
    """`duplicates` are the activities `find_duplicates` still reports; `version` is the chosen
    table, or None when the process has none."""
    if activity.status is ActivityStatus.REJEITADA:
        return _invalid(InvalidReason.REJEITADA)

    has_item = activity.group_number is not None and activity.item_number is not None
    criterion = None
    if version is not None and has_item:
        criterion = version.get_criterion(activity.group_number, activity.item_number)
    categorized = has_item if version is None else criterion is not None

    yearly = criterion is not None and is_yearly_unit(criterion.unit_label)
    if evaluate_period(activity, interstice, yearly) is PeriodState.FORA:
        return _invalid(InvalidReason.FORA_DO_INTERSTICIO, _outside_params(activity, interstice))

    if not categorized:
        return Validity(ValidityState.VALIDA, needs_category=True)
    if version is None or criterion is None:
        return Validity(ValidityState.VALIDA)

    group = version.get_group(criterion.group_number)
    if group is not None and not group.counts_in_total and not is_pit_criterion(version, criterion):
        return _invalid(InvalidReason.GRUPO_NAO_CONTA)
    if activity.id in duplicates:
        return _invalid(InvalidReason.DUPLICIDADE)
    if (
        criterion.min_hours is not None
        and activity.hours is not None
        and activity.hours < criterion.min_hours
    ):
        return _invalid(
            InvalidReason.CARGA_HORARIA_INSUFICIENTE,
            {"hours": activity.hours, "min_hours": criterion.min_hours},
        )
    return Validity(ValidityState.VALIDA)
