"""TAB-02, REL-02, PMOD-05, PMOD-12: Brazilian Portuguese formatting of dates, decimals, periods,
ranges, Roman numerals and the place and date line."""

from datetime import date
from decimal import Decimal

import pytest

from app.domain.rules.interstice import Interstice
from app.domain.rules.pt_format import (
    format_date,
    format_decimal,
    format_hours,
    format_interstice,
    format_long_date,
    format_period,
    format_place_date,
    to_roman,
)


def test_a_decimal_uses_a_comma_and_keeps_its_places():
    assert format_decimal(Decimal("52.00")) == "52,00"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (Decimal("0.00"), "0,00"),
        (Decimal("211"), "211"),
        (Decimal("7.5"), "7,5"),
        (Decimal("1234.50"), "1234,50"),
        (Decimal("-3.25"), "-3,25"),
        (Decimal("1E+2"), "100"),
    ],
)
def test_decimals_never_use_a_dot_or_an_exponent(value, expected):
    assert format_decimal(value) == expected


def test_an_integer_is_formatted_like_a_decimal_without_places():
    assert format_decimal(24) == "24"


def test_a_date_is_day_month_year_with_zero_padding():
    assert format_date(date(2024, 11, 23)) == "23/11/2024"
    assert format_date(date(2023, 3, 5)) == "05/03/2023"


@pytest.mark.parametrize(
    ("period", "expected"),
    [
        ("2023.1", "1º Período de 2023"),
        ("2024.2", "2º Período de 2024"),
        ("2020.3", "3º Período de 2020"),
    ],
)
def test_an_academic_period_reads_as_an_ordinal_period_of_the_year(period, expected):
    assert format_period(period) == expected


@pytest.mark.parametrize("text", ["", "2023", "primeiro", "2023.", "23.1"])
def test_a_period_out_of_the_format_is_written_as_typed(text):
    assert format_period(text) == text


@pytest.mark.parametrize(
    ("hours", "expected"),
    [
        (Decimal("60"), "60 h"),
        (Decimal("60.00"), "60 h"),
        (Decimal("7.5"), "7,5 h"),
        (Decimal("12.25"), "12,25 h"),
    ],
)
def test_course_hours_drop_trailing_zeros_and_end_with_h(hours, expected):
    assert format_hours(hours) == expected


def test_an_interstice_is_written_as_its_two_dates():
    interstice = Interstice(date(2022, 11, 23), date(2024, 11, 23))

    assert format_interstice(interstice) == "23/11/2022 a 23/11/2024"


def test_a_long_date_is_written_in_full_in_portuguese():
    assert format_long_date(date(2025, 3, 10)) == "10 de março de 2025"


@pytest.mark.parametrize(
    ("month", "name"),
    [
        (1, "janeiro"),
        (2, "fevereiro"),
        (3, "março"),
        (4, "abril"),
        (5, "maio"),
        (6, "junho"),
        (7, "julho"),
        (8, "agosto"),
        (9, "setembro"),
        (10, "outubro"),
        (11, "novembro"),
        (12, "dezembro"),
    ],
)
def test_each_month_of_a_long_date_has_its_portuguese_name(month, name):
    assert format_long_date(date(2026, month, 15)) == f"15 de {name} de 2026"


def test_the_first_day_of_a_long_date_has_no_zero_and_no_ordinal():
    assert format_long_date(date(2026, 1, 1)) == "1 de janeiro de 2026"


def test_a_leap_day_is_written_as_a_long_date():
    assert format_long_date(date(2024, 2, 29)) == "29 de fevereiro de 2024"


def test_a_long_date_does_not_depend_on_the_system_locale():
    import locale

    previous = locale.setlocale(locale.LC_TIME)
    try:
        for name in ("en_US.UTF-8", "fr_FR.UTF-8", "C"):
            try:
                locale.setlocale(locale.LC_TIME, name)
            except locale.Error:
                continue
            assert format_long_date(date(2025, 3, 10)) == "10 de março de 2025"
    finally:
        locale.setlocale(locale.LC_TIME, previous)


# --- Roman numerals (PMOD-12) ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("number", "roman"),
    [
        (1, "I"),
        (2, "II"),
        (3, "III"),
        (4, "IV"),
        (5, "V"),
        (9, "IX"),
        (10, "X"),
        (14, "XIV"),
        (40, "XL"),
        (90, "XC"),
        (400, "CD"),
        (1994, "MCMXCIV"),
        (3999, "MMMCMXCIX"),
    ],
)
def test_a_number_is_written_in_roman_numerals(number, roman):
    assert to_roman(number) == roman


@pytest.mark.parametrize("number", [0, -1, 4000])
def test_a_number_out_of_one_to_3999_has_no_roman_numeral(number):
    with pytest.raises(ValueError):
        to_roman(number)


# --- place and date line (PMOD-05) ----------------------------------------------------------


def test_the_place_and_date_line_has_the_day_without_zero_and_the_month_capitalized():
    assert format_place_date(date(2025, 4, 2)) == "2 de Abril de 2025"


@pytest.mark.parametrize(
    ("month", "name"),
    [
        (1, "Janeiro"),
        (2, "Fevereiro"),
        (3, "Março"),
        (4, "Abril"),
        (5, "Maio"),
        (6, "Junho"),
        (7, "Julho"),
        (8, "Agosto"),
        (9, "Setembro"),
        (10, "Outubro"),
        (11, "Novembro"),
        (12, "Dezembro"),
    ],
)
def test_each_month_of_the_place_and_date_line_has_a_capital_and_the_right_spelling(month, name):
    assert format_place_date(date(2026, month, 15)) == f"15 de {name} de 2026"


def test_the_day_of_the_place_and_date_line_has_a_zero_only_when_it_has_two_digits():
    assert format_place_date(date(2025, 5, 27)) == "27 de Maio de 2025"
    assert format_place_date(date(2025, 5, 7)) == "7 de Maio de 2025"


def test_a_leap_day_is_written_in_the_place_and_date_line():
    assert format_place_date(date(2024, 2, 29)) == "29 de Fevereiro de 2024"


def test_the_place_and_date_line_does_not_depend_on_the_system_locale():
    import locale

    previous = locale.setlocale(locale.LC_TIME)
    try:
        for name in ("en_US.UTF-8", "fr_FR.UTF-8", "C"):
            try:
                locale.setlocale(locale.LC_TIME, name)
            except locale.Error:
                continue
            assert format_place_date(date(2025, 3, 10)) == "10 de Março de 2025"
    finally:
        locale.setlocale(locale.LC_TIME, previous)
