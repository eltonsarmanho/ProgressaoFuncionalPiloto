"""Activity period evaluation against the interstice and title normalization (VERIF-01..04)."""

import calendar
import re
import unicodedata
from datetime import date
from enum import StrEnum

from app.domain.entities.activity import Activity, PeriodPrecision
from app.domain.rules.interstice import Interstice


class PeriodState(StrEnum):
    DENTRO = "DENTRO"
    PARCIAL = "PARCIAL"
    FORA = "FORA"
    SEM_DATA = "SEM_DATA"
    NAO_VERIFICAVEL = "NAO_VERIFICAVEL"


def expand_month_dates(start: date, end: date) -> tuple[date, date]:
    """First day of the start month to last day of the end month (VERIF-01)."""
    last_day = calendar.monthrange(end.year, end.month)[1]
    return start.replace(day=1), end.replace(day=last_day)


def is_yearly_unit(unit_label: str) -> bool:
    """Whether the unit of a table item is "por ano ..." (a function held for a time)."""
    return unit_label.strip().casefold().startswith("por ano")


def activity_interval(activity: Activity, open_end: date | None = None) -> tuple[date, date] | None:
    """Inclusive date range of the activity, or None when it has no date.

    A period with only a start date is one day, unless `open_end` is given: then it runs from
    the start to that date (the end of the interstice), or stays on its start when it began
    later (SEG-02). A dated event, a closed period and an end-only period never change.
    """
    start_only = (
        activity.event_date is None
        and activity.period_start is not None
        and activity.period_end is None
    )
    if start_only and open_end is not None:
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


def evaluate_period(
    activity: Activity, interstice: Interstice, open_ended: bool = False
) -> PeriodState:
    """`open_ended` reads a start-only period as running to the end of the interstice."""
    if interstice.end <= interstice.start:
        return PeriodState.NAO_VERIFICAVEL
    interval = activity_interval(activity, interstice.end if open_ended else None)
    if interval is None:
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
