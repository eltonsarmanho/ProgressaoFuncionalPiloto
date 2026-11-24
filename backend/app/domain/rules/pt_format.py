"""Brazilian Portuguese formatting of the values written in generated documents (TAB-02, REL-02).

Pure functions. Numbers carry a comma and no thousands separator, like the screen.
"""

import re
from datetime import date
from decimal import Decimal

from app.domain.rules.interstice import Interstice

_ACADEMIC_PERIOD = re.compile(r"^(\d{4})\.(\d)$")
_MONTH_NAMES = (
    "janeiro",
    "fevereiro",
    "março",
    "abril",
    "maio",
    "junho",
    "julho",
    "agosto",
    "setembro",
    "outubro",
    "novembro",
    "dezembro",
)


def format_decimal(value: Decimal | int) -> str:
    """`Decimal('52.00')` -> `52,00`; plain notation, never an exponent."""
    return format(Decimal(value), "f").replace(".", ",")


def format_date(value: date) -> str:
    """`date(2024, 11, 23)` -> `23/11/2024`."""
    return value.strftime("%d/%m/%Y")


def format_long_date(value: date) -> str:
    """`date(2025, 3, 10)` -> `10 de março de 2025`; no zero, no ordinal, no system locale."""
    return f"{value.day} de {_MONTH_NAMES[value.month - 1]} de {value.year}"


def format_place_date(value: date) -> str:
    """`date(2025, 4, 2)` -> `2 de Abril de 2025`: no zero, month capitalized (PMOD-05)."""
    return f"{value.day} de {_MONTH_NAMES[value.month - 1].capitalize()} de {value.year}"


_ROMAN = (
    (1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"),
    (50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I"),
)  # fmt: skip


def to_roman(n: int) -> str:
    """`4` -> `IV`, `1994` -> `MCMXCIV`; `ValueError` outside 1..3999."""
    if not 1 <= n <= 3999:
        raise ValueError(f"only 1 to 3999 has a Roman numeral, got {n}")
    out = []
    for value, symbol in _ROMAN:
        count, n = divmod(n, value)
        out.append(symbol * count)
    return "".join(out)


def format_period(period: str) -> str:
    """`2023.1` -> `1º Período de 2023`; text out of the AAAA.N format is returned as typed."""
    found = _ACADEMIC_PERIOD.match(period)
    if found is None:
        return period
    year, number = found.groups()
    return f"{number}º Período de {year}"


def format_hours(hours: Decimal) -> str:
    """`Decimal('60.00')` -> `60 h`; `Decimal('7.5')` -> `7,5 h`."""
    plain = format(hours.normalize(), "f")
    return f"{plain.replace('.', ',')} h"


def format_interstice(interstice: Interstice) -> str:
    """`23/11/2022 a 23/11/2024`."""
    return f"{format_date(interstice.start)} a {format_date(interstice.end)}"
