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
        # TER-01: halves, half a year, singular month and the exact ten-year limit
        ("por um ano e meio", 18),
        ("por 1 (um) ano e meio", 18),
        ("por dois anos e meio", 30),
        ("por 2 (dois) anos e meia", 30),
        ("por meio ano", 6),
        ("por 1 mês", 1),
        ("por um mes", 1),
        ("por 10 (dez) anos", 120),
        ("por 120 meses", 120),
        ("por 1 ano e 11 meses", 23),
        ("por 2 (dois) anos, 6 (seis) meses", 30),
        # TER-01: the term comes first, the extension after it is not part of it
        ("por 2 (dois) anos, prorrogável por mais 2 (dois) anos", 24),
        ("por 2 anos, podendo ser renovado por mais 1 ano", 24),
        ("por 1 ano, renovável por mais 6 meses", 12),
        ("por 2 anos prorrogáveis", 24),
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
        # TER-01: a term that is not certain
        "por 10 anos e 1 mês",  # above ten years by a month
        "por 121 meses",
        "por 1 ano e 12 meses",  # twelve months are a year: two spellings
        "por 1 ano e 13 meses",
        "por 1 mês e meio",  # a fraction of a month
        "por 2 anos e meio e 3 meses",
        "por 2 anos e meio ano",
        "por 2 anos (24 meses) e 3 meses",
        "por 2 anos, a partir de 09/08/2024 e por mais 6 meses",  # years and months apart
        "por 2 anos, ate o fim do mandato, mais 6 meses",
        "por 1 ano, por mais 1 ano",  # two year amounts
        "por 2 anos e 2 anos",
        "por 2 anos, 3 anos",
        "por 6 meses e por mais 6 meses",  # two month amounts
        "prorrogável por mais 2 anos",  # only the extension
        "renovado por 1 ano",
        "por 2,5 anos",  # decimals are not read
        "por 2.5 anos",
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
