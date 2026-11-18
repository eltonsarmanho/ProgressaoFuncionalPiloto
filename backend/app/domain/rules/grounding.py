"""Grounding: a value the AI returns only stays if it appears in the cited page (EXT-10, EXT-11).

All checks run against the ORIGINAL (unmasked) page text. The AI output is untrusted (AD-009):
a value that is not found becomes None and a NAO_ENCONTRADO_NO_TEXTO warning names the field.
"""

import re
from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal
from enum import StrEnum

from app.domain.entities.document import DocAlertCode
from app.domain.entities.extraction import ExtractedActivity
from app.domain.rules.number_words import numerals_from_words
from app.domain.rules.scoring_periods import normalize_title

MIN_TOKEN_LENGTH = 3
NAME_WINDOW_SLACK = 2  # extra words allowed between the tokens of a full name
TITLE_MIN_PERCENT = 90

_MONTHS = (
    ("janeiro", "jan"),
    ("fevereiro", "fev"),
    ("marco", "mar"),
    ("abril", "abr"),
    ("maio", "mai"),
    ("junho", "jun"),
    ("julho", "jul"),
    ("agosto", "ago"),
    ("setembro", "set"),
    ("outubro", "out"),
    ("novembro", "nov"),
    ("dezembro", "dez"),
)
_PARTICLES = frozenset({"de", "da", "do", "das", "dos", "e"})
_DATE_FIELDS = ("start_date", "end_date", "event_date")
_HOURS_FIELDS = ("hours", "course_hours")


class DatePrecision(StrEnum):
    DAY = "DAY"
    MONTH = "MONTH"
    YEAR = "YEAR"


@dataclass(frozen=True)
class GroundingWarning:
    code: DocAlertCode
    field: str


@dataclass(frozen=True)
class GroundingResult:
    activity: ExtractedActivity
    warnings: tuple[GroundingWarning, ...]
    grounded_ratio: Decimal


def _tokens(text: str) -> set[str]:
    return {
        t for t in re.findall(r"[a-z0-9]+", normalize_title(text)) if len(t) >= MIN_TOKEN_LENGTH
    }


def _month_name(month: int) -> str:
    full, abbr = _MONTHS[month - 1]
    return rf"(?:{full}|{abbr})\.?"


def date_in_text(value: date, text: str, precision: DatePrecision = DatePrecision.DAY) -> bool:
    """True when the date appears in the text with the given precision.

    Numbers written in words ("vinte e um de agosto de dois mil e vinte e quatro") count: the
    text is also searched with those words read as digits (REAL-04).
    """
    norm = normalize_title(text)
    candidates = dict.fromkeys((norm, numerals_from_words(norm)))
    return any(_date_found(value, candidate, precision) for candidate in candidates)


def _date_found(value: date, norm: str, precision: DatePrecision) -> bool:
    year = rf"{value.year}"
    if precision is DatePrecision.YEAR:
        return re.search(rf"(?<!\d){year}(?!\d)", norm) is not None
    month = value.month
    if precision is DatePrecision.MONTH:
        two_digit_year = f"{value.year % 100:02d}"
        named = (
            rf"(?<![a-z]){_month_name(month)}\s*(?:[/.\-,]|de|do\s+ano(?:\s+de)?)?\s*"
            rf"(?:{year}|{two_digit_year})(?!\d)"
        )
        numeric = rf"(?<![\d/.\-])0?{month}\s?[/.\-]\s?{year}(?!\d)"
        return re.search(f"{named}|{numeric}", norm) is not None
    day = value.day
    sep = r"\s?[/.\-]\s?"
    numeric = rf"(?<!\d)0?{day}{sep}0?{month}{sep}{year}(?!\d)"
    iso = rf"(?<!\d){year}{sep}0?{month}{sep}0?{day}(?!\d)"
    # the day may be an end of a range ("18 a 22 de maio de 2026"); the other end is any day
    any_day, link = r"\d{1,2}o?", r"\s*(?:a|ate|e|-|/)\s*"
    day_part = rf"(?:(?<!\d){any_day}{link})?(?<!\d)0?{day}o?(?:{link}{any_day})?"
    # a range may cross months and share the year: "28 de abril a 2 de maio de 2026"
    other_month = rf"(?:{link}{any_day}(?:\s+de)?\s+[a-z]{{3,9}}\.?)?"
    spelled = (
        rf"{day_part}(?:\s+dias?)?(?:\s+do\s+mes)?(?:\s+de)?\s+(?<![a-z]){_month_name(month)}"
        rf"{other_month}\s*(?:de\s+|do\s+ano\s+(?:de\s+)?|,\s*|/\s*)?{year}(?!\d)"
    )
    return re.search(f"{numeric}|{iso}|{spelled}", norm) is not None


def hours_in_text(value: Decimal, text: str) -> bool:
    """True when the number appears as a token (68, 68h, 68 horas, 68,5, 1.200, 08 horas)."""
    plain = format(value.normalize(), "f")
    forms = {plain, plain.replace(".", ",")}
    integer, _, fraction = plain.partition(".")
    if len(integer) > 3 and not fraction:
        forms.add(f"{int(integer):,}".replace(",", "."))
    pattern = "|".join(re.escape(f) for f in forms)
    return re.search(rf"(?<![\d.,])0*(?:{pattern})(?![.,]?\d)", text) is not None


def _alnum(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", normalize_title(text))


def identifier_in_text(value: str, text: str) -> bool:
    """Normalized substring match, ignoring spaces, punctuation, case and accents."""
    reduced = _alnum(value)
    return bool(reduced) and reduced in _alnum(text)


def title_in_text(value: str, text: str) -> bool:
    """True when at least 90% of the title tokens (3+ letters) appear in the text."""
    tokens = _tokens(value)
    if not tokens:
        return identifier_in_text(value, text)
    found = len(tokens & _tokens(text))
    return found * 100 >= len(tokens) * TITLE_MIN_PERCENT


def name_in_text(value: str, text: str) -> bool:
    """True when every token (3+ letters) of the name appears in the text."""
    tokens = _tokens(value)
    return bool(tokens) and tokens <= _tokens(text)


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", normalize_title(text))


def professor_named_in_text(professor_name: str, text: str) -> bool:
    """True when the whole name (2+ tokens of 3+ letters) sits together in the text.

    Case, accents, order ("SOBRENOME, Nome") and the particles "de", "da", "dos" do not matter,
    but the tokens must fall within a short window of words, so the same words scattered over
    a page that names other people do not count as the professor (REAL-02).
    """
    wanted = _tokens(professor_name)
    if len(wanted) < 2:
        return False
    words = _words(text)
    width = len(wanted) + NAME_WINDOW_SLACK
    for index, word in enumerate(words):
        if word in wanted and wanted <= set(words[index : index + width]):
            return True
    return False


def _words_in_text(wanted: list[str], text: str) -> bool:
    """True when the words appear one after the other in the text (the form as written)."""
    words = _words(text)
    return bool(wanted) and any(
        words[i : i + len(wanted)] == wanted for i in range(len(words) - len(wanted) + 1)
    )


def _abbreviation_of(extracted_name: str, professor_name: str) -> bool:
    """"M. A. Souza" or "SOUZA, M. A." for "Maria Aparecida de Souza" (REAL-03).

    The last surname must be equal and every given-name token must be the full name or the
    initial of the professor's given name at the same position.
    At least one token must be an initial; names written in full are a partial name.
    """
    professor = [w for w in _words(professor_name) if w not in _PARTICLES]
    if len(professor) < 2:
        return False
    if "," in extracted_name:
        surname_part, _, given_part = extracted_name.partition(",")
        surname, given = _words(surname_part), _words(given_part)
        surname = surname[-1:] if surname else []
    else:
        parts = _words(extracted_name)
        surname, given = parts[-1:], parts[:-1]
    given = [w for w in given if w not in _PARTICLES]
    if not surname or not given or len(given) > len(professor) - 1:
        return False
    if surname[0] != professor[-1] or len(surname[0]) < MIN_TOKEN_LENGTH:
        return False
    if not any(len(token) == 1 for token in given):
        return False  # no initial: a partial name, not an abbreviation (SEG-08)
    return all(
        token == professor[i] or (len(token) == 1 and token == professor[i][0])
        for i, token in enumerate(given)
    )


def same_person(
    extracted_name: str | None, professor_name: str, siape: str | None, text: str
) -> bool:
    """True when the names match by tokens (3+ letters), by abbreviation or the SIAPE is in text.

    A partial name (two or more of the professor's names) counts only when the professor's
    whole name is in the text (SEG-08); the SIAPE in the text decides by itself. An abbreviated
    name ("M. A. Souza") fits every person with those initials, so it counts only when the
    professor's full name is also in the text or the abbreviated form itself is written in the
    text (VER-13).
    """
    if extracted_name:
        extracted, professor = _tokens(extracted_name), _tokens(professor_name)
        if professor and professor <= extracted:
            return True
        if len(extracted) >= 2 and extracted <= professor:
            # a partial name fits other people too: the whole name must be in the text (SEG-08)
            if professor_named_in_text(professor_name, text):
                return True
        if _abbreviation_of(extracted_name, professor_name) and (
            professor_named_in_text(professor_name, text)
            or _words_in_text(_words(extracted_name), text)
        ):
            return True
    return bool(siape) and re.search(rf"(?<!\d){re.escape(siape)}(?!\d)", text) is not None


def month_only_dates(
    extracted: ExtractedActivity, pages: Mapping[int, str]
) -> dict[str, DatePrecision]:
    """Date fields the page writes with month and year only (VER-10): field -> MONTH.

    A field qualifies when the AI gave the first day of the month, that day is not in the text
    but the month and year are. Any other day for a month-only text is invented: it does not
    qualify and `ground` nulls it. Never invents a day.
    """
    text = pages.get(extracted.page, "")
    partial: dict[str, DatePrecision] = {}
    for name in _DATE_FIELDS:
        value = getattr(extracted, name)
        if value is None or value.day != 1:
            continue
        if not date_in_text(value, text) and date_in_text(value, text, DatePrecision.MONTH):
            partial[name] = DatePrecision.MONTH
    return partial


def ground(
    extracted: ExtractedActivity,
    pages: Mapping[int, str],
    precisions: Mapping[str, DatePrecision] | None = None,
) -> GroundingResult:
    """Null every value missing from the cited page; return warnings and the found ratio.

    The ratio is the fraction of non-null verifiable fields found in the text; it is 0 when
    there is nothing to verify. `precisions` maps a date field name to a coarser precision.
    """
    text = pages.get(extracted.page, "")
    precisions = precisions or {}
    checks: dict[str, bool] = {}
    for name in ("title", "identifier", "term"):
        value = getattr(extracted, name)
        if value is not None:
            check = title_in_text if name == "title" else identifier_in_text
            checks[name] = check(value, text)
    for name in _DATE_FIELDS:
        value = getattr(extracted, name)
        if value is not None:
            checks[name] = date_in_text(value, text, precisions.get(name, DatePrecision.DAY))
    for name in _HOURS_FIELDS:
        value = getattr(extracted, name)
        if value is not None:
            checks[name] = hours_in_text(value, text)
    failed = [name for name, ok in checks.items() if not ok]
    grounded = replace(extracted, **dict.fromkeys(failed))
    warnings = tuple(GroundingWarning(DocAlertCode.NAO_ENCONTRADO_NO_TEXTO, f) for f in failed)
    ratio = Decimal(len(checks) - len(failed)) / Decimal(len(checks)) if checks else Decimal(0)
    return GroundingResult(activity=grounded, warnings=warnings, grounded_ratio=ratio)
