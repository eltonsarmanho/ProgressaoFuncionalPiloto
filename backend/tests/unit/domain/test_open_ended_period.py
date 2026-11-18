"""SEG-02: a start-only period of a yearly item is open ended; other items keep one day."""

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

from app.domain.entities.activity import Activity, ActivityStatus, PeriodPrecision
from app.domain.entities.scoring import (
    ScoringCriterion,
    ScoringGroup,
    ScoringMode,
    ScoringTableVersion,
    TableStatus,
)
from app.domain.rules.interstice import Interstice
from app.domain.rules.scoring_alerts import NotScoredReason, ScoringAlertCode
from app.domain.rules.scoring_engine import RowStatus, calculate
from app.domain.rules.scoring_periods import PeriodState, activity_interval, evaluate_period

INTERSTICE = Interstice(date(2024, 11, 23), date(2026, 11, 23))


def activity(**kwargs) -> Activity:
    return Activity(id=uuid4(), process_id=uuid4(), title="Diretor", created_by=uuid4(), **kwargs)


def test_the_interval_of_a_start_only_period_is_one_day_unless_an_open_end_is_given():
    start_only = activity(period_start=date(2025, 3, 1))
    assert activity_interval(start_only) == (date(2025, 3, 1), date(2025, 3, 1))
    assert activity_interval(start_only, INTERSTICE.end) == (date(2025, 3, 1), INTERSTICE.end)


def test_an_open_end_never_applies_to_a_dated_or_closed_period():
    closed = activity(period_start=date(2025, 3, 1), period_end=date(2025, 5, 1))
    event = activity(event_date=date(2025, 3, 1), period_start=date(2025, 3, 1))
    end_only = activity(period_end=date(2025, 3, 1))
    assert activity_interval(closed, INTERSTICE.end) == (date(2025, 3, 1), date(2025, 5, 1))
    assert activity_interval(event, INTERSTICE.end) == (date(2025, 3, 1), date(2025, 3, 1))
    assert activity_interval(end_only, INTERSTICE.end) == (date(2025, 3, 1), date(2025, 3, 1))


def test_an_open_period_starting_after_the_interstice_end_stays_at_its_start():
    late = activity(period_start=date(2027, 1, 10))
    assert activity_interval(late, INTERSTICE.end) == (date(2027, 1, 10), date(2027, 1, 10))


def test_open_ended_start_inside_the_interstice_is_dentro():
    a = activity(period_start=date(2026, 8, 9))
    assert evaluate_period(a, INTERSTICE, open_ended=True) is PeriodState.DENTRO


def test_open_ended_start_before_the_interstice_is_parcial_and_after_its_end_is_fora():
    before = activity(period_start=date(2024, 8, 9))
    after = activity(period_start=date(2026, 11, 24))
    assert evaluate_period(before, INTERSTICE, open_ended=True) is PeriodState.PARCIAL
    assert evaluate_period(after, INTERSTICE, open_ended=True) is PeriodState.FORA


def test_without_the_open_flag_a_start_only_period_is_still_one_day():
    before = activity(period_start=date(2024, 8, 9))
    assert evaluate_period(before, INTERSTICE) is PeriodState.FORA


def test_open_ended_month_precision_starts_at_the_first_day_of_the_month():
    a = activity(period_start=date(2024, 11, 1), period_precision=PeriodPrecision.MONTH)
    assert activity_interval(a, INTERSTICE.end) == (date(2024, 11, 1), INTERSTICE.end)


def criterion(group, item, unit_label) -> ScoringCriterion:
    return ScoringCriterion(
        group, item, f"item {group}.{item}", unit_label, ScoringMode.POR_UNIDADE,
        unit_points=Decimal(30),
    )  # fmt: skip


TABLE = ScoringTableVersion(
    table_id=None,
    name="Tabela de teste",
    valid_from=date(2020, 1, 1),
    valid_to=None,
    norm_reference="norma",
    status=TableStatus.OFICIAL,
    groups=(
        ScoringGroup(6, "VI", criteria=(criterion(6, 6, "por ano de exercício"),)),
        ScoringGroup(7, "VII", criteria=(criterion(7, 10, "por ação"),)),
    ),
)


def scored(group, item, **kwargs) -> Activity:
    return activity(
        group_number=group,
        item_number=item,
        quantity=Decimal(1),
        evidence_note="portaria",
        status=ActivityStatus.AGUARDANDO_REVISAO,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        **kwargs,
    )


def test_the_engine_reads_a_start_only_yearly_item_as_open_ended():
    director = scored(6, 6, period_start=date(2024, 8, 9))
    row = calculate(TABLE, [director], INTERSTICE).rows[0]
    assert row.status is RowStatus.POTENCIAL
    assert row.points == Decimal(30)
    assert ScoringAlertCode.INTERSTICIO_PARCIAL in [alert.code for alert in row.alerts]


def test_the_engine_keeps_the_single_day_of_a_start_only_item_that_is_not_yearly():
    course = scored(7, 10, period_start=date(2024, 8, 9))
    row = calculate(TABLE, [course], INTERSTICE).rows[0]
    assert row.status is RowStatus.NAO_PONTUADA
    assert row.reasons == (NotScoredReason.FORA_DO_INTERSTICIO,)


def test_the_engine_leaves_a_yearly_item_after_the_interstice_out():
    director = scored(6, 6, period_start=date(2026, 11, 24))
    row = calculate(TABLE, [director], INTERSTICE).rows[0]
    assert row.reasons == (NotScoredReason.FORA_DO_INTERSTICIO,)
