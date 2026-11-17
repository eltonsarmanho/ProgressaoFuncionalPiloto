"""Quality of a page text layer and of OCR output (PIPE-05, PIPE-07).

Useful characters are letters and digits (Unicode, accents included). The symbol ratio is the
share of non-whitespace characters that are neither useful nor common punctuation.
"""

import re
from decimal import Decimal

MIN_USEFUL_CHARS = 50
MAX_SYMBOL_PERCENT = 30
IMAGE_HEAVY_COVERAGE = 0.5  # share of the page covered by images that makes it "image heavy"
MIN_DISTINCT_WORDS = 60  # a text layer with fewer distinct words may be only header and footer
MIN_OCR_CONFIDENCE = Decimal("60")

_COMMON_PUNCTUATION = frozenset(".,;:!?-()/\"'%ºª°§&@#+“”‘’–—…")


def _is_useful(char: str) -> bool:
    # The ordinal indicators are Unicode letters but behave as punctuation in "nº" and "1ª".
    return char.isalnum() and char not in "ºª"


def _is_symbol(char: str) -> bool:
    return not (_is_useful(char) or char.isspace() or char in _COMMON_PUNCTUATION)


def is_text_layer_usable(text: str) -> bool:
    """False when there are fewer than 50 useful characters or more than 30% symbols."""
    useful = sum(1 for c in text if _is_useful(c))
    if useful < MIN_USEFUL_CHARS:
        return False
    visible = sum(1 for c in text if not c.isspace())
    symbols = sum(1 for c in text if _is_symbol(c))
    return symbols * 100 <= visible * MAX_SYMBOL_PERCENT


def is_text_layer_thin(text: str, image_coverage: float) -> bool:
    """True for a page that is mostly image and whose text layer has few distinct words.

    A scanned certificate can keep a header and a footer as text while the body is a picture;
    such a layer passes `is_text_layer_usable` but misses the content (REAL-13).
    """
    if image_coverage < IMAGE_HEAVY_COVERAGE:
        return False
    words = {w for w in re.findall(r"[^\W\d_]{3,}", text.casefold())}
    return len(words) < MIN_DISTINCT_WORDS


def ocr_needs_review(confidence: Decimal | None, text: str) -> bool:
    """True for no text or a mean OCR confidence below 60 (alert TEXTO_ILEGIVEL)."""
    if not text.strip() or confidence is None:
        return True
    return confidence < MIN_OCR_CONFIDENCE
