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
_AMOUNT = re.compile(r"(?<![\d/.])(\d{1,3})\s*(?:\(\s*(\d{1,3})\s*\)\s*)?(anos?|meses|mes)\b")


def parse_term_months(text: str) -> int | None:
    """Months of a term such as "por 2 (dois) anos"; None when it is not read with certainty.

    The number may be in digits, in words or both ("2 (dois)"); digits and words that
    disagree, a missing unit, zero, more than ten years or two spellings of the same unit
    ("2 anos (24 meses)") are not read. Years and months may be combined once each.
    """
    normalized = numerals_from_words(normalize_title(text))
    years = months = None
    for amount, written, unit in _AMOUNT.findall(normalized):
        if written and written != amount:
            return None
        count = int(amount)
        if unit.startswith("ano"):
            if years is not None:
                return None
            years = count
        else:
            if months is not None:
                return None
            months = count
    if years is None and months is None:
        return None
    if years is not None and months is not None and months >= 12:
        return None
    total = (years or 0) * 12 + (months or 0)
    return total if 0 < total <= MAX_TERM_YEARS * 12 else None


def add_months(day: date, months: int) -> date:
    """The same day `months` later; a day past the end of the month falls on its last day."""
    year, month = divmod(day.year * 12 + day.month - 1 + months, 12)
    month += 1
    last_day = calendar.monthrange(year, month)[1]
    return day.replace(year=year, month=month, day=min(day.day, last_day))
