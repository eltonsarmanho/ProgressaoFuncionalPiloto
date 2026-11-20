"""The duration of a designation, read from its wording, and the end date it implies (SEG-01).

"por 2 (dois) anos", "24 meses" or "pelo período de um ano" give a number of months; anything
that is not certain gives None, so an end date is never made up (AD-009, AD-010). Numbers in
words go through the same reader the date grounding uses.
"""

import calendar
import re
from datetime import date

from app.domain.rules.number_words import numerals_from_words
from app.domain.rules.scoring_periods import normalize_title

MAX_TERM_YEARS = 10
_AMOUNT = re.compile(
    r"(?<![\d/.,])(\d{1,3})\s*(?:\(\s*(\d{1,3})\s*\)\s*)?(anos?|meses|mes)\b"
    r"(\s+e\s+(?:meio|meia)\b)?"
)
_HALF_YEAR = re.compile(r"\bmeio\s+ano\b")
_BETWEEN_YEARS_AND_MONTHS = re.compile(r"[\s,]*(?:e[\s,]+)?")
# the extension of a term ("prorrogável por mais 2 anos") is not the term itself
_EXTENSION = re.compile(r"\b(?:prorrog\w*|renov\w*|podendo\s+ser|passivel\s+de)\b")


def parse_term_months(text: str) -> int | None:
    """Months of a term such as "por 2 (dois) anos"; None when it is not read with certainty.

    The number may be in digits, in words or both ("2 (dois)"); "e meio" adds six months to
    years and "meio ano" is six months. Digits and words that disagree, a missing unit, zero,
    more than ten years, a fraction of a month, decimals, two amounts of the same unit and
    years and months that are not written together ("2 anos e 6 meses") are not read. Only
    the text before an extension ("prorrogável por mais 2 anos") is the term; an extension
    alone is not (SEG-01, TER-01).
    """
    normalized = numerals_from_words(normalize_title(text))
    extension = _EXTENSION.search(normalized)
    if extension:
        normalized = normalized[: extension.start()]
    if _HALF_YEAR.search(normalized):
        return 6 if _AMOUNT.search(normalized) is None else None
    years = months = None
    half_year = False
    previous_end = None
    for found in _AMOUNT.finditer(normalized):
        amount, written, unit, half = found.groups()
        if written and written != amount:
            return None
        count = int(amount)
        if unit.startswith("ano"):
            if years is not None:
                return None
            years, half_year = count, bool(half)
        else:
            if months is not None or half:
                return None
            months = count
        if previous_end is not None and not _BETWEEN_YEARS_AND_MONTHS.fullmatch(
            normalized, previous_end, found.start()
        ):
            return None
        previous_end = found.end()
    if years is None and months is None:
        return None
    if half_year and months is not None:
        return None
    if years is not None and months is not None and months >= 12:
        return None
    total = (years or 0) * 12 + (months or 0) + (6 if half_year else 0)
    return total if 0 < total <= MAX_TERM_YEARS * 12 else None


def add_months(day: date, months: int) -> date:
    """The same day `months` later; a day past the end of the month falls on its last day."""
    year, month = divmod(day.year * 12 + day.month - 1 + months, 12)
    month += 1
    last_day = calendar.monthrange(year, month)[1]
    return day.replace(year=year, month=month, day=min(day.day, last_day))
