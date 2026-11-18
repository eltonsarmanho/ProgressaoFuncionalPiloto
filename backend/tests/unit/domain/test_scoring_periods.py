"""VERIF-01..04 and the invalid-interstice edge case; title normalization (VERIF-05)."""

from datetime import date
from uuid import uuid4

import pytest

from app.domain.entities.activity import Activity, PeriodPrecision
from app.domain.rules.interstice import Interstice
from app.domain.rules.scoring_periods import (
    PeriodState,
    evaluate_period,
    expand_month_dates,
    normalize_title,
)

INTERSTICE = Interstice(date(2022, 11, 23), date(2024, 11, 23))


def _activity(**kwargs) -> Activity:
    return Activity(id=uuid4(), process_id=uuid4(), title="Atividade", created_by=uuid4(), **kwargs)


def test_month_range_expands_to_first_and_last_day():
    # "Mai/22 a Mai/22"
    assert expand_month_dates(date(2022, 5, 1), date(2022, 5, 1)) == (
        date(2022, 5, 1),
        date(2022, 5, 31),
    )


def test_month_range_expansion_handles_leap_february():
    assert expand_month_dates(date(2024, 2, 10), date(2024, 2, 10)) == (
        date(2024, 2, 1),
        date(2024, 2, 29),
    )


def test_month_range_spanning_months_expands_both_ends():
    assert expand_month_dates(date(2023, 2, 1), date(2023, 4, 1)) == (
        date(2023, 2, 1),
        date(2023, 4, 30),
    )


def test_month_activity_inside_interstice_is_dentro():
    activity = _activity(
        period_start=date(2023, 5, 1),
        period_end=date(2023, 5, 1),
        period_precision=PeriodPrecision.MONTH,
    )

    assert evaluate_period(activity, INTERSTICE) is PeriodState.DENTRO


def test_november_2022_month_against_interstice_starting_on_23rd_is_parcial():
    activity = _activity(
        period_start=date(2022, 11, 1),
        period_end=date(2022, 11, 1),
        period_precision=PeriodPrecision.MONTH,
    )

    assert evaluate_period(activity, INTERSTICE) is PeriodState.PARCIAL


def test_month_entirely_before_interstice_is_fora():
    activity = _activity(
        period_start=date(2022, 5, 1),
        period_end=date(2022, 5, 1),
        period_precision=PeriodPrecision.MONTH,
    )

    assert evaluate_period(activity, INTERSTICE) is PeriodState.FORA


def test_event_before_interstice_is_fora():
    assert evaluate_period(_activity(event_date=date(2022, 11, 22)), INTERSTICE) is PeriodState.FORA


def test_event_after_interstice_is_fora():
    assert evaluate_period(_activity(event_date=date(2024, 11, 24)), INTERSTICE) is PeriodState.FORA


@pytest.mark.parametrize("edge", [date(2022, 11, 23), date(2024, 11, 23)])
def test_event_on_interstice_limits_is_dentro(edge):
    assert evaluate_period(_activity(event_date=edge), INTERSTICE) is PeriodState.DENTRO


def test_period_crossing_the_start_is_parcial():
    activity = _activity(period_start=date(2022, 10, 1), period_end=date(2022, 12, 1))

    assert evaluate_period(activity, INTERSTICE) is PeriodState.PARCIAL


def test_period_crossing_the_end_is_parcial():
    activity = _activity(period_start=date(2024, 10, 1), period_end=date(2025, 2, 1))

    assert evaluate_period(activity, INTERSTICE) is PeriodState.PARCIAL


def test_period_covering_the_whole_interstice_is_parcial():
    activity = _activity(period_start=date(2022, 1, 1), period_end=date(2025, 1, 1))

    assert evaluate_period(activity, INTERSTICE) is PeriodState.PARCIAL


def test_period_inside_interstice_is_dentro():
    activity = _activity(period_start=date(2023, 3, 1), period_end=date(2023, 6, 30))

    assert evaluate_period(activity, INTERSTICE) is PeriodState.DENTRO


def test_period_without_overlap_is_fora():
    activity = _activity(period_start=date(2025, 1, 1), period_end=date(2025, 6, 30))

    assert evaluate_period(activity, INTERSTICE) is PeriodState.FORA


def test_activity_without_any_date_is_sem_data():
    assert evaluate_period(_activity(), INTERSTICE) is PeriodState.SEM_DATA


@pytest.mark.parametrize(
    "interstice",
    [
        Interstice(date(2024, 11, 23), date(2022, 11, 23)),
        Interstice(date(2024, 11, 23), date(2024, 11, 23)),
    ],
)
def test_invalid_interstice_is_nao_verificavel(interstice):
    activity = _activity(event_date=date(2023, 1, 1))

    assert evaluate_period(activity, interstice) is PeriodState.NAO_VERIFICAVEL


def test_invalid_interstice_is_nao_verificavel_even_without_date():
    interstice = Interstice(date(2024, 1, 1), date(2023, 1, 1))

    assert evaluate_period(_activity(), interstice) is PeriodState.NAO_VERIFICAVEL


def test_normalize_title_ignores_case_accents_and_repeated_spaces():
    assert normalize_title("  Comissão   de  AVALIAÇÃO ") == "comissao de avaliacao"
    assert normalize_title("Comissão de Avaliação") == normalize_title("comissao   de avaliacao")


def test_normalize_title_keeps_different_titles_different():
    assert normalize_title("Comissão A") != normalize_title("Comissão B")
