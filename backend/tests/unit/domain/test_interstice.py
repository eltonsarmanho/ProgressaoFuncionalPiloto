"""PROC-02 and interstice edge cases (spec Assumptions: contagem de meses; Edge Cases)."""

from datetime import date

import pytest

from app.domain.rules.interstice import Interstice

RESTRUCTURING = date(2025, 1, 1)


@pytest.mark.parametrize(
    ("start", "end", "months"),
    [
        (date(2024, 11, 23), date(2026, 11, 23), 24),  # spec example
        (date(2024, 11, 23), date(2026, 11, 22), 23),  # spec example
        (date(2022, 11, 23), date(2024, 11, 23), 24),  # PROC-10 case
        (date(2024, 2, 29), date(2026, 2, 28), 24),  # edge case: 29/02 in leap year
        (date(2022, 12, 31), date(2024, 12, 31), 24),  # interstice ending 31/12/2024
    ],
)
def test_months_counts_full_civil_months(start, end, months):
    assert Interstice(start, end).months() == months


def test_end_of_month_adjustment_only_applies_on_last_day_of_month():
    # 28/02/2026 is the last day of Feb 2026 -> month completed;
    # 27/02/2026 is not -> month incomplete.
    assert Interstice(date(2024, 2, 29), date(2026, 2, 27)).months() == 23


@pytest.mark.parametrize(
    ("start", "end", "days"),
    [
        (date(2024, 11, 23), date(2026, 11, 23), 730),
        (date(2022, 11, 23), date(2024, 11, 23), 731),  # includes 29/02/2024
        (date(2024, 2, 29), date(2026, 2, 28), 730),
    ],
)
def test_days_is_calendar_day_difference(start, end, days):
    assert Interstice(start, end).days() == days


@pytest.mark.parametrize(
    ("start", "end", "expected"),
    [
        (date(2024, 11, 23), date(2026, 11, 23), True),  # PROC-11 case
        (date(2024, 12, 31), date(2025, 1, 1), True),  # ends exactly on the date
        (date(2022, 11, 23), date(2024, 12, 31), False),  # ends the day before
        (date(2025, 1, 1), date(2027, 1, 1), False),  # starts exactly on the date
        (date(2022, 11, 23), date(2024, 11, 23), False),  # PROC-10 case
    ],
)
def test_crosses_requires_start_before_and_end_on_or_after(start, end, expected):
    assert Interstice(start, end).crosses(RESTRUCTURING) is expected
