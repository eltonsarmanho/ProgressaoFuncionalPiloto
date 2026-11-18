"""SEG-01: the duration of a designation read from its wording, and the end date from it."""

from datetime import date

import pytest

from app.domain.rules.term_rules import add_months, parse_term_months


@pytest.mark.parametrize(
    ("text", "months"),
    [
        ("por 2 (dois) anos", 24),
        ("por dois anos", 24),
        ("por mais 2 anos", 24),
        ("24 meses", 24),
        ("vinte e quatro meses", 24),
        ("pelo período de um ano", 12),
        ("pelo período de 1 (um) ano", 12),
        ("mandato de quatro (4) anos", 48),
        ("por 1 ano e 6 meses", 18),
        ("por seis meses", 6),
        ("PELO PERÍODO DE DOIS ANOS", 24),
    ],
)
def test_the_term_is_read_in_months(text, months):
    assert parse_term_months(text) == months


@pytest.mark.parametrize(
    "text",
    [
        "por 3 (dois) anos",  # digit and word disagree
        "por alguns anos",
        "a partir de 09/08/2024",
        "por 2",  # no unit
        "",
        "por 2 anos (24 meses)",  # two spellings of the same term: not read
        "por 0 anos",
        "por 40 anos",  # above ten years
    ],
)
def test_a_term_that_is_not_certain_is_not_read(text):
    assert parse_term_months(text) is None


@pytest.mark.parametrize(
    ("start", "months", "end"),
    [
        (date(2024, 8, 9), 24, date(2026, 8, 9)),
        (date(2024, 8, 9), 12, date(2025, 8, 9)),
        (date(2024, 8, 9), 18, date(2026, 2, 9)),
        (date(2024, 1, 31), 1, date(2024, 2, 29)),  # the day is kept inside the month
        (date(2023, 11, 30), 3, date(2024, 2, 29)),
        (date(2024, 12, 15), 2, date(2025, 2, 15)),
    ],
)
def test_the_end_is_the_start_plus_the_term(start, months, end):
    assert add_months(start, months) == end
