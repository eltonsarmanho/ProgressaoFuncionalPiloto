"""PMOD-08, PMOD-09: Portuguese cardinal numbers written in words, from 1 to 2999."""

import pytest

from app.domain.rules.number_words import numerals_from_words
from app.domain.rules.scoring_periods import normalize_title
from app.domain.rules.spelled_numbers import spell_number

TABLE = [
    (1, "um"),
    (2, "dois"),
    (3, "três"),
    (10, "dez"),
    (16, "dezesseis"),
    (20, "vinte"),
    (21, "vinte e um"),
    (27, "vinte e sete"),
    (31, "trinta e um"),
    (100, "cem"),
    (101, "cento e um"),
    (110, "cento e dez"),
    (200, "duzentos"),
    (999, "novecentos e noventa e nove"),
    (1000, "mil"),
    (1001, "mil e um"),
    (1100, "mil e cem"),
    (1101, "mil cento e um"),
    (1999, "mil novecentos e noventa e nove"),
    (2000, "dois mil"),
    (2020, "dois mil e vinte"),
    (2025, "dois mil e vinte e cinco"),
    (2026, "dois mil e vinte e seis"),
    (2100, "dois mil e cem"),
    (2101, "dois mil cento e um"),
    (2200, "dois mil e duzentos"),
    (2999, "dois mil novecentos e noventa e nove"),
]


@pytest.mark.parametrize(("number", "words"), TABLE)
def test_a_number_is_written_in_words_with_the_connector_of_portuguese(number, words):
    assert spell_number(number) == words


@pytest.mark.parametrize("number", [0, -1, 3000])
def test_a_number_out_of_one_to_2999_is_refused(number):
    with pytest.raises(ValueError):
        spell_number(number)


def test_the_project_reader_of_number_words_reads_back_every_number_written_here():
    wrong = [
        n for n in range(1, 3000) if numerals_from_words(normalize_title(spell_number(n))) != str(n)
    ]

    assert wrong == []
