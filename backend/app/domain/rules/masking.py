"""Masking of personal identifiers before text goes to the AI service (EXT-07).

CPF, RG, e-mail and phone become markers. Names, SIAPE, process and ordinance numbers,
CNPJ, dates, hours, academic periods, DOI and ISSN stay as they are.
"""

import re
from collections import Counter
from dataclasses import dataclass, field


@dataclass(frozen=True)
class MaskedText:
    text: str
    counts: dict[str, int] = field(default_factory=dict)


_EMAIL = re.compile(r"[\w.+%-]+@[\w-]+(?:\.[\w-]+)+")

_RG_LABEL = r"(?<!\w)(?:R\.?\s?G\.?|Identidade|Registro\s+Geral)(?!\w)\s*(?:n[ºo°.]{0,2}\s*)?:?\s*"
_RG_ISSUER = r"(?:\s*[-/]?\s*(?:SSP|SESP|SJ|PC|IFP|DETRAN|DGPC|PM)\s*[/-]?\s*[A-Z]{2}\b)?"
_RG = re.compile(rf"({_RG_LABEL})\d[\d.\-]{{4,13}}[\dXx]{_RG_ISSUER}", re.IGNORECASE)

_CPF_FORMATTED = re.compile(r"(?<!\d)\d{3}\.\d{3}\.\d{3}-\d{2}(?!\d)")
_CPF_BARE = re.compile(r"(?<!\d[.\-/])(?<!\d)\d{11}(?!\d)(?![.\-/]\d)")

_PHONE_PARENS = re.compile(r"(?<!\w)(?:\+?55\s?)?\(\d{2}\)\s?9?\d{4}[\s-]?\d{4}(?!\d)")
_PHONE_COUNTRY = re.compile(r"(?<!\w)\+55\s?\d{2}\s?9?\d{4}[\s-]?\d{4}(?!\d)")
_PHONE_MOBILE = re.compile(r"(?<![\w.\-/])\d{2}[\s-]9\d{4}[\s-]?\d{4}(?!\d)")
# Landline with a bare DDD: skip two years in a row such as "10 2024-2025".
_PHONE_LANDLINE = re.compile(
    r"(?<![\w.\-/])[1-9][1-9]\s[2-5]\d{3}-\d{4}(?![\d.\-/])(?<!\s(?:19|20)\d{2}-(?:19|20)\d{2})"
)
_PHONE_LOCAL_MOBILE = re.compile(r"(?<![\w.\-/])9\d{4}-\d{4}(?![\d.\-/])")


def mask_identifiers(text: str) -> MaskedText:
    """Return a copy of `text` with identifiers replaced by markers; the input is untouched."""
    counts: Counter[str] = Counter()

    def sub(pattern: re.Pattern[str], marker: str, current: str, keep_label: bool = False) -> str:
        def repl(match: re.Match[str]) -> str:
            counts[marker] += 1
            return (match.group(1) if keep_label else "") + f"[{marker}]"

        return pattern.sub(repl, current)

    result = sub(_EMAIL, "EMAIL", text)
    result = sub(_RG, "RG", result, keep_label=True)
    result = sub(_CPF_FORMATTED, "CPF", result)
    result = sub(_CPF_BARE, "CPF", result)
    for phone in (
        _PHONE_PARENS,
        _PHONE_COUNTRY,
        _PHONE_MOBILE,
        _PHONE_LANDLINE,
        _PHONE_LOCAL_MOBILE,
    ):
        result = sub(phone, "TELEFONE", result)
    return MaskedText(text=result, counts=dict(counts))
