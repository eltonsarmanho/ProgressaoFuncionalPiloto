"""Similarity of activity titles: sets of words, and the proper-name guard (SEG-04, TER-08).

The AI writes the title of a repeated certificate differently each time, so two titles of the
same item count as alike when their sets of words are close (Jaccard). Titles of bancas or
orientations differ by the name of the student or of the board member, though, and a name makes
a different activity: a capitalized word of three letters or more on each side with no alike
word on the other side is a proper name, and such titles are never alike. A typo of the OCR
("Academica"/"Academia"), a word in lowercase or an extra word on one side only is not a name.
"""

import re
from difflib import SequenceMatcher

from app.domain.rules.scoring_periods import normalize_title

SIMILAR_TITLE_JACCARD = 0.8
REPEATED_TITLE_JACCARD = 0.6  # noisy copies of one activity inside one document
MIN_NAME_LENGTH = 3
TYPO_RATIO = 0.8  # two words this alike are one word written twice (OCR), not two names
_WORD = re.compile(r"[^\W\d_]+|\d+")
_ROMAN = re.compile(r"(?:I{1,3}|IV|VI{0,3}|IX|X{1,3})")


def title_words(title: str) -> frozenset[str]:
    return frozenset(re.findall(r"[a-z0-9]+", normalize_title(title)))


def jaccard(one: str, two: str) -> float:
    """Jaccard similarity of the sets of normalized words of two titles."""
    words_one, words_two = title_words(one), title_words(two)
    union = words_one | words_two
    return len(words_one & words_two) / len(union) if union else 0.0


def _capitalized(title: str) -> set[str]:
    """Normalized words written with a capital first letter, 3 letters or more."""
    return {
        normalize_title(word)
        for word in _WORD.findall(title)
        if len(word) >= MIN_NAME_LENGTH and word[0].isupper()
    }


def _unmatched_names(names: set[str], other_words: frozenset[str]) -> set[str]:
    """Names with no equal or alike word in the other title."""
    return {
        name
        for name in names
        if all(SequenceMatcher(None, name, word).ratio() < TYPO_RATIO for word in other_words)
    }


def differ_by_proper_name(one: str, two: str) -> bool:
    """True when each title has a proper name that the other title does not have."""
    words_one, words_two = title_words(one), title_words(two)
    return bool(
        _unmatched_names(_capitalized(one), words_two)
        and _unmatched_names(_capitalized(two), words_one)
    )


def _variant_marks(title: str) -> set[str]:
    """Numerals, Roman numerals and lone capital letters of a title ("1", "III", "B")."""
    return {
        normalize_title(word)
        for word in _WORD.findall(title)
        if word.isdigit() or (word.isupper() and (len(word) == 1 or _ROMAN.fullmatch(word)))
    }


def differ_by_numeral(one: str, two: str) -> bool:
    """True when each title has a numeral or lone letter that the other does not have.

    "Nível 1" and "Nível 2", "Turma A" and "Turma B", "Cálculo I" and "Cálculo II" are variants
    of a course, not two copies of it (QUA-05). A mark on one side only is OCR noise or a year.
    """
    words_one, words_two = title_words(one), title_words(two)
    return bool(_variant_marks(one) - words_two and _variant_marks(two) - words_one)


def similar_titles(one: str, two: str, threshold: float = SIMILAR_TITLE_JACCARD) -> bool:
    """Alike by the Jaccard of the words, and not different by a proper name."""
    return jaccard(one, two) >= threshold and not differ_by_proper_name(one, two)


def repeated_titles(one: str, two: str) -> bool:
    """Two titles of one document that are the same activity written twice (TER-07).

    A Jaccard of 0.6 or more, or the words of one title inside the other (OCR noise adds words
    and breaks them), and no proper name or numeral on each side.
    """
    words_one, words_two = title_words(one), title_words(two)
    if not words_one or not words_two:
        return False
    close = (
        jaccard(one, two) >= REPEATED_TITLE_JACCARD
        or words_one <= words_two
        or words_two <= words_one
    )
    return close and not differ_by_proper_name(one, two) and not differ_by_numeral(one, two)
