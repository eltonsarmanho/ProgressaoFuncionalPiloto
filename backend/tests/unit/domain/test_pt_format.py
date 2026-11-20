"""TAB-02, REL-02: Brazilian Portuguese formatting of dates, decimals, periods and ranges."""

from datetime import date
from decimal import Decimal

import pytest

from app.domain.rules.interstice import Interstice
from app.domain.rules.pt_format import (
    format_date,
    format_decimal,
    format_hours,
    format_interstice,
    format_period,
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
