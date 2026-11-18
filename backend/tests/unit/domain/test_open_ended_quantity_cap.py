"""TER-05: an open ended yearly activity scores at most the complete years inside the interstice.

A start-only period of a "por ano" item (hand entered or suggested) runs to the end of the
interstice. The quantity scored is the smaller of the quantity typed and the complete years of
that period inside the interstice (no quantity typed: the complete years); it is never raised
above what the person typed. The row carries `DATA_FIM_AUSENTE`.
"""

from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.entities.activity import Activity, ActivityStatus, PeriodPrecision
from app.domain.entities.scoring import (
    ScoringCriterion,
    ScoringGroup,
    ScoringMode,
    ScoringTableVersion,
    TableStatus,
)
from app.domain.rules.interstice import Interstice
from app.domain.rules.scoring_alerts import ScoringAlertCode
from app.domain.rules.scoring_duplicates import find_duplicates
from app.domain.rules.scoring_engine import RowStatus, calculate

INTERSTICE = Interstice(date(2024, 11, 23), date(2026, 11, 23))  # exactly two complete years


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


def entered(group=6, item=6, quantity=None, **dates) -> Activity:
    return Activity(
        id=uuid4(),
        process_id=uuid4(),
        title="Funcao",
        created_by=uuid4(),
        group_number=group,
        item_number=item,
        quantity=None if quantity is None else Decimal(quantity),
        evidence_note="portaria",
        status=ActivityStatus.AGUARDANDO_REVISAO,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        **dates,
    )


def row_of(activity):
    return calculate(TABLE, [activity], INTERSTICE).rows[0]


def codes(row):
    return [alert.code for alert in row.alerts]


def test_a_typed_quantity_above_the_years_inside_the_interstice_is_capped():
    row = row_of(entered(quantity=3, period_start=date(2020, 1, 1)))
    assert row.effective_quantity == Decimal(2)
    assert row.points == Decimal(60)  # was 90
    assert row.status is RowStatus.POTENCIAL
    assert ScoringAlertCode.DATA_FIM_AUSENTE in codes(row)
    assert ScoringAlertCode.INTERSTICIO_PARCIAL in codes(row)


def test_a_typed_quantity_below_the_years_is_never_raised():
    row = row_of(entered(quantity=1, period_start=date(2020, 1, 1)))
    assert row.effective_quantity == Decimal(1)
    assert row.points == Decimal(30)
    assert ScoringAlertCode.DATA_FIM_AUSENTE in codes(row)


def test_a_typed_zero_stays_zero():
    row = row_of(entered(quantity=0, period_start=date(2020, 1, 1)))
    assert row.effective_quantity == Decimal(0)
    assert row.points == Decimal(0)


def test_without_a_typed_quantity_the_complete_years_inside_the_interstice_count():
    inside = row_of(entered(period_start=date(2024, 8, 9)))  # runs from the interstice start
    later = row_of(entered(period_start=date(2025, 3, 1)))  # 2025-03-01 to 2026-11-23: one year
    assert (inside.effective_quantity, inside.points) == (Decimal(2), Decimal(60))
    assert (later.effective_quantity, later.points) == (Decimal(1), Decimal(30))


def test_less_than_a_complete_year_inside_the_interstice_scores_zero():
    row = row_of(entered(quantity=3, period_start=date(2026, 8, 9)))
    assert row.effective_quantity == Decimal(0)
    assert row.points == Decimal(0)
    assert ScoringAlertCode.DATA_FIM_AUSENTE in codes(row)


def test_the_start_day_of_a_month_precision_period_is_the_first_of_the_month():
    row = row_of(
        entered(period_start=date(2025, 11, 30), period_precision=PeriodPrecision.MONTH)
    )
    assert row.effective_quantity == Decimal(1)  # from 2025-11-01 to 2026-11-23


@pytest.mark.parametrize(
    "dates",
    [
        {"period_start": date(2024, 8, 9), "period_end": date(2025, 1, 31)},  # closed period
        {"event_date": date(2025, 3, 1), "period_start": date(2020, 1, 1)},  # dated event
    ],
)
def test_a_closed_period_or_a_dated_event_keeps_the_typed_quantity_and_no_open_end_alert(dates):
    row = row_of(entered(quantity=3, **dates))
    assert row.effective_quantity == Decimal(3)
    assert ScoringAlertCode.DATA_FIM_AUSENTE not in codes(row)


def test_an_item_that_is_not_yearly_keeps_the_typed_quantity():
    row = row_of(entered(group=7, item=10, quantity=3, period_start=date(2025, 3, 1)))
    assert row.effective_quantity == Decimal(3)
    assert ScoringAlertCode.DATA_FIM_AUSENTE not in codes(row)


def test_two_unclassified_activities_with_alike_titles_are_not_the_same_item():
    def loose(title):
        return Activity(
            id=uuid4(),
            process_id=uuid4(),
            title=title,
            created_by=uuid4(),
            event_date=date(2025, 3, 1),
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
        )

    stem = "Oficina de dados abertos para gestores publicos de pequenos municipios"
    one, two = loose(f"{stem} brasileiros"), loose(f"{stem} amazonicos")
    assert find_duplicates([one, two]) == set()
    classified = [replace(a, group_number=7, item_number=10) for a in (one, two)]
    assert len(find_duplicates(classified)) == 1  # the same titles are duplicates in one item
