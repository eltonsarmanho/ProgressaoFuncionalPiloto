"""Activity period evaluation against the interstice and title normalization (VERIF-01..04)."""

import calendar
import re
import unicodedata
from datetime import date
from enum import StrEnum

from app.domain.entities.activity import Activity, PeriodPrecision
from app.domain.rules.interstice import Interstice

ACADEMIC_PERIOD = re.compile(r"\d{4}\.\d")


class PeriodState(StrEnum):
    DENTRO = "DENTRO"
    PARCIAL = "PARCIAL"
    FORA = "FORA"
    SEM_DATA = "SEM_DATA"
    NAO_VERIFICAVEL = "NAO_VERIFICAVEL"


def has_academic_period(activity: Activity) -> bool:
    """Whether the activity carries a well-formed academic period (AAAA.N), as the offers of
    group I do instead of a date."""
    period = activity.academic_period
    return period is not None and ACADEMIC_PERIOD.fullmatch(period) is not None


def expand_month_dates(start: date, end: date) -> tuple[date, date]:
    """First day of the start month to last day of the end month (VERIF-01)."""
    last_day = calendar.monthrange(end.year, end.month)[1]
    return start.replace(day=1), end.replace(day=last_day)


def is_yearly_unit(unit_label: str) -> bool:
    """Whether the unit of a table item is "por ano ..." (a function held for a time)."""
    return unit_label.strip().casefold().startswith("por ano")


def is_start_only(activity: Activity) -> bool:
    """A start date with neither an end date nor a single event date (SEG-02)."""
    return (
        activity.event_date is None
        and activity.period_start is not None
        and activity.period_end is None
    )


def complete_years_between(start: date, end: date) -> int:
    years = end.year - start.year
    if (end.month, end.day) < (start.month, start.day):
        years -= 1
    return years


def complete_years_inside(start: date, end: date, interstice: Interstice) -> int:
    """Complete years of [start, end] that fall inside the interstice; 0 when none (TER-05)."""
    start, end = max(start, interstice.start), min(end, interstice.end)
    return 0 if end < start else complete_years_between(start, end)


def open_period_years(activity: Activity, interstice: Interstice) -> int:
    """Complete years of a start-only period that runs to the end of the interstice."""
    start = activity.period_start
    if start is None:
        return 0
    if activity.period_precision is PeriodPrecision.MONTH:
        start = start.replace(day=1)
    return complete_years_inside(start, interstice.end, interstice)


def activity_interval(activity: Activity, open_end: date | None = None) -> tuple[date, date] | None:
    """Inclusive date range of the activity, or None when it has no date.

    A period with only a start date is one day, unless `open_end` is given: then it runs from
    the start to that date (the end of the interstice), or stays on its start when it began
    later (SEG-02). A dated event, a closed period and an end-only period never change.
    """
    if is_start_only(activity) and open_end is not None:
        start = activity.period_start
        if activity.period_precision is PeriodPrecision.MONTH:
            start = start.replace(day=1)
        return start, max(start, open_end)
    if activity.event_date is not None:
        start = end = activity.event_date
    elif activity.period_start is not None or activity.period_end is not None:
        start = activity.period_start or activity.period_end
        end = activity.period_end or activity.period_start
    else:
        return None
    if activity.period_precision is PeriodPrecision.MONTH:
        return expand_month_dates(start, end)
    return start, end


def _term_year_is_outside(activity: Activity, interstice: Interstice) -> bool:
    """Whether the whole year of the academic period (AAAA.N) lies outside the interstice.

    Semester dates are not invented: only a year with no day inside the interstice is outside.
    """
    year = int(activity.academic_period[:4])
    return date(year, 12, 31) < interstice.start or date(year, 1, 1) > interstice.end


def evaluate_period(
    activity: Activity, interstice: Interstice, open_ended: bool = False
) -> PeriodState:
    """`open_ended` reads a start-only period as running to the end of the interstice.

    A group I offer with no date and no period of dates is judged by the year of its academic
    period: FORA when the whole year is outside the interstice, otherwise SEM_DATA (GI-09).
    """
    if interstice.end <= interstice.start:
        return PeriodState.NAO_VERIFICAVEL
    interval = activity_interval(activity, interstice.end if open_ended else None)
    if interval is None:
        if (
            activity.group_number == 1
            and has_academic_period(activity)
            and _term_year_is_outside(activity, interstice)
        ):
            return PeriodState.FORA
        return PeriodState.SEM_DATA
    start, end = interval
    if end < interstice.start or start > interstice.end:
        return PeriodState.FORA
    if start >= interstice.start and end <= interstice.end:
        return PeriodState.DENTRO
    return PeriodState.PARCIAL


def normalize_title(text: str) -> str:
    """Lowercase, accent-free, with runs of whitespace collapsed to one space."""
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", stripped).strip().casefold()
