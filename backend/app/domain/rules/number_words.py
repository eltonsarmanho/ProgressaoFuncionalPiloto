"""Portuguese cardinal numbers written in words, read as digits (REAL-04).

Used only to check dates and numbers the AI returned against a page that writes them out
("vinte e um dias do mês de agosto do ano de dois mil e vinte e quatro"). The input is the
accent-free, lowercase text of `normalize_title`; every other character is kept as it was.
"""

import re

_UNITS = {
    "um": 1, "uma": 1, "primeiro": 1, "dois": 2, "duas": 2, "tres": 3, "quatro": 4,
    "cinco": 5, "seis": 6, "sete": 7, "oito": 8, "nove": 9,
}  # fmt: skip
_TEENS = {
    "dez": 10, "onze": 11, "doze": 12, "treze": 13, "catorze": 14, "quatorze": 14,
    "quinze": 15, "dezesseis": 16, "dezasseis": 16, "dezessete": 17, "dezassete": 17,
    "dezoito": 18, "dezenove": 19, "dezanove": 19,
}  # fmt: skip
_TENS = {
    "vinte": 20, "trinta": 30, "quarenta": 40, "cinquenta": 50, "sessenta": 60,
    "setenta": 70, "oitenta": 80, "noventa": 90,
}  # fmt: skip
_HUNDREDS = {
    "cem": 100, "cento": 100, "duzentos": 200, "trezentos": 300, "quatrocentos": 400,
    "quinhentos": 500, "seiscentos": 600, "setecentos": 700, "oitocentos": 800,
    "novecentos": 900,
}  # fmt: skip
_THOUSAND = "mil"
_NUMBER_WORDS = {*_UNITS, *_TEENS, *_TENS, *_HUNDREDS, _THOUSAND}
_TOKEN = re.compile(r"[a-z0-9]+")


def _fits(word: str, chunk: int) -> bool:
    """Whether `word` can follow the hundreds-tens-units value built so far (below 1000)."""
    if word in _HUNDREDS:
        return chunk == 0
    below_hundred = chunk % 100
    if word in _TENS or word in _TEENS:
        return below_hundred == 0
    return below_hundred % 10 == 0 and not 10 <= below_hundred < 20  # a unit


def _read_number(words: list[str], joined: list[bool], start: int) -> tuple[int, int] | None:
    """The value of the number phrase starting at `start` and the index after its last word.

    `joined[i]` says word i follows word i-1 with only whitespace between them.
    """
    total = chunk = 0
    end = None
    index = start
    while index < len(words):
        word = words[index]
        if index > start and not joined[index]:
            break
        if word == "e" and end is not None and index + 1 < len(words):
            index += 1  # connector: only kept when a number word follows
            continue
        if word not in _NUMBER_WORDS:
            break
        if word == _THOUSAND:
            if chunk >= 1000 or total % 1000:
                break
            total += (chunk or 1) * 1000
            chunk = 0
        elif _fits(word, chunk):
            chunk += _UNITS.get(word) or _TEENS.get(word) or _TENS.get(word) or _HUNDREDS[word]
        else:
            break
        index += 1
        end = index
    if end is None:
        return None
    return total + chunk, end


def numerals_from_words(text: str) -> str:
    """The text with each run of number words replaced by its digits.

    Runs are words separated by whitespace only, so a number never crosses punctuation.
    """
    tokens = list(_TOKEN.finditer(text))
    words = [t.group() for t in tokens]
    joined = [
        i > 0 and text[tokens[i - 1].end() : tokens[i].start()].isspace()
        for i in range(len(tokens))
    ]
    out: list[str] = []
    copied = 0  # text up to here is already in `out`
    index = 0
    while index < len(tokens):
        found = _read_number(words, joined, index) if words[index] in _NUMBER_WORDS else None
        if found is None:
            index += 1
            continue
        value, end = found
        out.append(text[copied : tokens[index].start()])
        out.append(str(value))
        copied = tokens[end - 1].end()
        index = end
    out.append(text[copied:])
    return "".join(out)
