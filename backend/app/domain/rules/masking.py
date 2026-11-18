"""Masking of personal identifiers before text goes to the AI service (EXT-07).

CPF, RG, e-mail and phone become markers. Names, SIAPE, process and ordinance numbers,
CNPJ, dates, hours, academic periods, DOI and ISSN stay as they are. OCR text makes spaced or
line-split CPF likely (VER-05); a landline without area code is masked only after a phone label,
because a bare "2345-2350" is a page range or an ISSN.
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
# "CI 1234567" (carteira de identidade); a memo number such as "CI 45/2025" has a slash and stays.
_CI_LABEL = r"(?<!\w)C\.?I\.?(?!\w)\s*(?:n[ºo°.]{0,2}\s*)?:?\s*"
_CI = re.compile(
    rf"({_CI_LABEL})\d{{1,2}}\.?\d{{3}}\.?\d{{3}}(?:-?[\dXx])?{_RG_ISSUER}(?![\d/])",
    re.IGNORECASE,
)
# RG without a label, only in the formatted pattern "12.345.678-9" (a CNPJ has a slash).
_RG_UNLABELED = re.compile(r"(?<![\d.\-/])\d{1,2}\.\d{3}\.\d{3}-[\dXx](?![\d/\-])")

_CPF_FORMATTED = re.compile(r"(?<!\d)\d{3}\.\d{3}\.\d{3}-\d{2}(?!\d)")
# CPF written with spaces, or split by a line break (OCR): "123 456 789 09", "123.456.789-\n09".
_CPF_SEP = r"(?:\s{0,3}[.\-]\s{0,3}|\s{1,3})"
_CPF_LOOSE = re.compile(
    rf"(?<![\w.\-/])\d{{3}}{_CPF_SEP}\d{{3}}{_CPF_SEP}\d{{3}}{_CPF_SEP}\d{{2}}(?![\d]|[.\-/]\d)"
)
_CPF_BARE = re.compile(r"(?<!\d[.\-/])(?<!\d)\d{11}(?!\d)(?![.\-/]\d)")

_PHONE_PARENS = re.compile(r"(?<!\w)(?:\+?55\s?)?\(\d{2}\)\s?9?\d{4}[\s-]?\d{4}(?!\d)")
_PHONE_COUNTRY = re.compile(r"(?<!\w)\+55\s?\d{2}\s?9?\d{4}[\s-]?\d{4}(?!\d)")
_PHONE_MOBILE = re.compile(r"(?<![\w.\-/])\d{2}[\s-]9\d{4}[\s-]?\d{4}(?!\d)")
# Landline with a bare DDD: skip two years in a row such as "10 2024-2025".
_PHONE_LANDLINE = re.compile(
    r"(?<![\w.\-/])[1-9][1-9]\s[2-5]\d{3}-\d{4}(?![\d.\-/])(?<!\s(?:19|20)\d{2}-(?:19|20)\d{2})"
)
_PHONE_LOCAL_MOBILE = re.compile(r"(?<![\w.\-/])9\d{4}-\d{4}(?![\d.\-/])")
# Landline without area code, only after a phone label: "fone 3201-7777" (a bare "2345-2350"
# is a page range or an ISSN, so it needs the label).
_PHONE_LABEL = r"(?<!\w)(?:telefone|tel|fone|fax|celular|contato|ramal|whatsapp)\b[\s.:\-]{0,4}"
_PHONE_LOCAL_LANDLINE = re.compile(
    rf"({_PHONE_LABEL})[2-5]\d{{3}}[\s-]\d{{4}}(?!\d|[.\-/]\d)", re.IGNORECASE
)
_PHONE_SPACED_DDD = re.compile(
    r"(?<![\w.\-/])[1-9][1-9]\s[2-5]\d{3}\s\d{4}(?![\d.\-/])(?<!\s(?:19|20)\d{2}\s(?:19|20)\d{2})"
)


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
    result = sub(_CI, "RG", result, keep_label=True)
    result = sub(_CPF_FORMATTED, "CPF", result)
    result = sub(_CPF_LOOSE, "CPF", result)
    result = sub(_RG_UNLABELED, "RG", result)
    result = sub(_CPF_BARE, "CPF", result)
    result = sub(_PHONE_LOCAL_LANDLINE, "TELEFONE", result, keep_label=True)
    for phone in (
        _PHONE_PARENS,
        _PHONE_COUNTRY,
        _PHONE_MOBILE,
        _PHONE_LANDLINE,
        _PHONE_SPACED_DDD,
        _PHONE_LOCAL_MOBILE,
    ):
        result = sub(phone, "TELEFONE", result)
    return MaskedText(text=result, counts=dict(counts))
