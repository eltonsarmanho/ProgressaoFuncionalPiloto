"""Final confidence of an extracted activity (EXT-12)."""

from decimal import ROUND_HALF_UP, Decimal

REVIEW_THRESHOLD = Decimal("0.70")
_TWO_PLACES = Decimal("0.01")


def _check_range(value: Decimal) -> None:
    if not Decimal(0) <= value <= Decimal(1):
        raise ValueError(f"confidence must be between 0 and 1, got {value}")


def final_confidence(llm_confidence: Decimal, grounded_ratio: Decimal) -> Decimal:
    """The lower of the AI confidence and the grounded ratio, rounded to two places."""
    _check_range(llm_confidence)
    _check_range(grounded_ratio)
    return min(llm_confidence, grounded_ratio).quantize(_TWO_PLACES, rounding=ROUND_HALF_UP)


def needs_review(confidence: Decimal) -> bool:
    """True below 0.70; 0.70 itself does not need review."""
    _check_range(confidence)
    return confidence < REVIEW_THRESHOLD
