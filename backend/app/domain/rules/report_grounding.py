"""Conference of the wording the AI proposes for a report entry (REL-04, REL-12, AD-009).

The text from the AI is untrusted: it only stays when every number and date it carries is in the
fields that were sent. A refused text is replaced by the template text. Everything is compared
accent-free and with number words read as digits, like the grounding of the extraction.
"""

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from enum import StrEnum

from app.domain.rules.grounding import _MONTHS, DatePrecision, date_in_text, hours_in_text
from app.domain.rules.number_words import numerals_from_words
from app.domain.rules.scoring_periods import normalize_title


class WordingReason(StrEnum):
    NUMERO = "NUMERO"
    DATA = "DATA"


@dataclass(frozen=True)
class WordingVocabulary:
    """Configuration of the conference: names, words and the limit of new words."""

    max_new_words: int
    allowed_terms: tuple[str, ...] = ()
    formal_vocabulary: tuple[str, ...] = ()
    forbidden_words: tuple[str, ...] = ()


@dataclass(frozen=True)
class WordingCheck:
    """`text` is the wording when it is accepted and the template text when it is not."""

    accepted: bool
    reasons: tuple[WordingReason, ...]
    text: str


_MONTH_NUMBER = {full: number for number, (full, _) in enumerate(_MONTHS, start=1)}
_MONTH = "(" + "|".join(_MONTH_NUMBER) + ")"
_TENS = "vinte|trinta|quarenta|cinquenta|sessenta|setenta|oitenta|noventa"
_ONE = re.compile(rf"\b(?:(?P<tens>{_TENS}) e )?(?P<one>um|uma)\b")  # "uma oficina" is no number
_ORDINAL = re.compile(
    r"\b(primeira|segund[oa]|terceir[oa]|quart[oa]|quint[oa]|sext[oa]|setim[oa]|oitav[oa]|"
    r"non[oa]|decim[oa])(?=\s+(?:semestre|periodo|ano|edicao|turma|fase|etapa|modulo|"
    r"bimestre|trimestre|lugar)\b)"
)
_ORDINAL_VALUE = {
    "primeira": 1, "segund": 2, "terceir": 3, "quart": 4, "quint": 5,
    "sext": 6, "setim": 7, "oitav": 8, "non": 9, "decim": 10,
}  # fmt: skip
_SPELLED_DAY = re.compile(
    rf"(?<!\d)(\d{{1,2}})o?\s+(?:dias?\s+)?(?:do\s+mes\s+)?de\s+{_MONTH}\s+"
    r"(?:de\s+|do\s+ano\s+(?:de\s+)?)?(\d{4})(?!\d)"
)
_NUMERIC_DAY = re.compile(r"(?<![\d/.\-])(\d{1,2})\s?[/.\-]\s?(\d{1,2})\s?[/.\-]\s?(\d{4})(?!\d)")
_SPELLED_MONTH = re.compile(
    rf"(?<![a-z]){_MONTH}\s*(?:de\s+|do\s+ano\s+(?:de\s+)?|/|,\s*)?(\d{{4}})(?!\d)"
)
_NUMERIC_MONTH = re.compile(r"(?<![\d/.\-])(\d{1,2})\s?/\s?(\d{4})(?!\d)")
_ACADEMIC_PERIOD = re.compile(r"(?<!\d)(\d{4})\.([1-9])(?!\d)")
_NUMBER = re.compile(r"\d+(?:[.,]\d+)*")
_THOUSANDS = re.compile(r"\d{1,3}(?:[.,]\d{3})+")


def _ordinal_digit(found: re.Match[str]) -> str:
    word = found.group(1)
    return str(_ORDINAL_VALUE.get(word, _ORDINAL_VALUE.get(word[:-1], 0)))


def _article(found: re.Match[str]) -> str:
    return found.group(0) if found.group("tens") else "artigo"


def _numeric_view(text: str) -> str:
    """Accent-free text with number words, ordinals and academic periods written as digits.

    "um" and "uma" are articles, except at the end of a number such as "vinte e um".
    """
    view = _ONE.sub(_article, normalize_title(text))
    view = _ORDINAL.sub(_ordinal_digit, numerals_from_words(view))
    return _ACADEMIC_PERIOD.sub(r"\1 \2", view)


@dataclass(frozen=True)
class _Mention:
    year: int
    month: int
    day: int | None


def _mentions(view: str) -> tuple[list[_Mention], str]:
    """The dates written in the text and the text without them."""
    found: list[_Mention] = []

    def spelled_day(match: re.Match[str]) -> str:
        found.append(_Mention(int(match[3]), _MONTH_NUMBER[match[2]], int(match[1])))
        return " "

    def numeric_day(match: re.Match[str]) -> str:
        found.append(_Mention(int(match[3]), int(match[2]), int(match[1])))
        return " "

    def spelled_month(match: re.Match[str]) -> str:
        found.append(_Mention(int(match[2]), _MONTH_NUMBER[match[1]], None))
        return " "

    def numeric_month(match: re.Match[str]) -> str:
        found.append(_Mention(int(match[2]), int(match[1]), None))
        return " "

    rest = _SPELLED_DAY.sub(spelled_day, view)
    rest = _NUMERIC_DAY.sub(numeric_day, rest)
    rest = _SPELLED_MONTH.sub(spelled_month, rest)
    rest = _NUMERIC_MONTH.sub(numeric_month, rest)
    return found, rest


def _date_is_grounded(mention: _Mention, facts_text: str, fact_mentions: list[_Mention]) -> bool:
    try:
        if mention.day is not None:
            return date_in_text(date(mention.year, mention.month, mention.day), facts_text)
        month_start = date(mention.year, mention.month, 1)
    except ValueError:
        return False
    if date_in_text(month_start, facts_text, DatePrecision.MONTH):
        return True
    return any(f.year == mention.year and f.month == mention.month for f in fact_mentions)


def _values(token: str) -> list[Decimal]:
    """The numbers a token can be: "1.200" is 1.2 or 1200, "7,5" is 7.5."""
    readings = [token.replace(",", ".")]
    if _THOUSANDS.fullmatch(token):
        readings.append(re.sub(r"[.,]", "", token))
    values = []
    for reading in readings:
        try:
            values.append(Decimal(reading))
        except InvalidOperation:
            continue
    return values


def _number_reasons(wording: str, facts_text: str) -> set[WordingReason]:
    reasons: set[WordingReason] = set()
    facts_view = _numeric_view(facts_text)
    fact_mentions, _ = _mentions(facts_view)
    mentions, rest = _mentions(_numeric_view(wording))
    if not all(_date_is_grounded(m, facts_text, fact_mentions) for m in mentions):
        reasons.add(WordingReason.DATA)
    for token in _NUMBER.findall(rest):
        if not any(hours_in_text(value, facts_view) for value in _values(token)):
            reasons.add(WordingReason.NUMERO)
    return reasons


def check_wording(
    wording: str, facts: Mapping[str, str], vocabulary: WordingVocabulary, model_text: str
) -> WordingCheck:
    """Accept the wording only when what it states is in the fields that were sent."""
    reasons = _number_reasons(wording, "\n".join(facts.values()))
    ordered = tuple(r for r in WordingReason if r in reasons)
    return WordingCheck(not ordered, ordered, model_text if ordered else wording)
