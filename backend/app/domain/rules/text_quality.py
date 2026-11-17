"""Quality of a page text layer and of OCR output (PIPE-05, PIPE-07).

Useful characters are letters and digits (Unicode, accents included). The symbol ratio is the
share of non-whitespace characters that are neither useful nor common punctuation.
"""

from decimal import Decimal

MIN_USEFUL_CHARS = 50
MAX_SYMBOL_PERCENT = 30
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


def ocr_needs_review(confidence: Decimal | None, text: str) -> bool:
    """True for no text or a mean OCR confidence below 60 (alert TEXTO_ILEGIVEL)."""
    if not text.strip() or confidence is None:
        return True
    return confidence < MIN_OCR_CONFIDENCE
