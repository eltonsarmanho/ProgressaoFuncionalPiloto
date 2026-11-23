"""Portuguese cardinal numbers written in words (PMOD-08, PMOD-09).

Pure function, the inverse of `numerals_from_words`. Covers 1 to 2999: the days of a month and
the years a Parecer can carry.
"""

_UNITS = (
    "", "um", "dois", "três", "quatro", "cinco", "seis", "sete", "oito", "nove", "dez", "onze",
    "doze", "treze", "catorze", "quinze", "dezesseis", "dezessete", "dezoito", "dezenove",
)  # fmt: skip
_TENS = (
    "", "", "vinte", "trinta", "quarenta", "cinquenta", "sessenta", "setenta", "oitenta", "noventa",
)  # fmt: skip
_HUNDREDS = (
    "", "cento", "duzentos", "trezentos", "quatrocentos", "quinhentos", "seiscentos",
    "setecentos", "oitocentos", "novecentos",
)  # fmt: skip
_MAX = 2999


def _below_thousand(n: int) -> str:
    """1 to 999."""
    if n == 100:
        return "cem"
    hundreds, rest = divmod(n, 100)
    parts = [_HUNDREDS[hundreds]] if hundreds else []
    if rest:
        tens, units = divmod(rest, 10)
        parts.append(
            _UNITS[rest] if rest < 20 else _TENS[tens] + (f" e {_UNITS[units]}" if units else "")
        )
    return " e ".join(parts)


def spell_number(n: int) -> str:
    """`27` -> `vinte e sete`, `2025` -> `dois mil e vinte e cinco`; `ValueError` outside 1..2999.

    After "mil" the "e" appears only when the rest is below 100 or a round hundred.
    """
    if not 1 <= n <= _MAX:
        raise ValueError(f"only 1 to {_MAX} can be written in words, got {n}")
    thousands, rest = divmod(n, 1000)
    if not thousands:
        return _below_thousand(rest)
    head = "mil" if thousands == 1 else f"{_UNITS[thousands]} mil"
    if not rest:
        return head
    joint = " e " if rest < 100 or rest % 100 == 0 else " "
    return f"{head}{joint}{_below_thousand(rest)}"
