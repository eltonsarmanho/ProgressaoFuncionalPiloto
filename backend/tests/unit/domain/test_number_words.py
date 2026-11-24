"""REAL-04: Portuguese cardinals in words read as digits, for the date check."""

import pytest

from app.domain.rules.number_words import numerals_from_words


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("vinte e um dias do mes de agosto", "21 dias do mes de agosto"),
        ("do ano de dois mil e vinte e quatro", "do ano de 2024"),
        ("primeiro de maio de dois mil e dezenove", "1 de maio de 2019"),
        ("trinta e um de dezembro de dois mil", "31 de dezembro de 2000"),
        ("mil novecentos e noventa e nove", "1999"),
        ("cento e vinte horas", "120 horas"),
    ],
)
def test_runs_of_number_words_become_digits(text, expected):
    assert numerals_from_words(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("dois, tres e quatro", "2, 3 e 4"),
        ("um e dois", "1 e 2"),
        ("dois tres", "2 3"),
        ("21 de agosto de 2024", "21 de agosto de 2024"),
        ("sem numeros por extenso", "sem numeros por extenso"),
    ],
)
def test_separate_numbers_and_plain_text_are_not_merged_or_changed(text, expected):
    assert numerals_from_words(text) == expected
