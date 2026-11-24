"""EXT-12: final confidence is the lower of the AI value and the grounded ratio."""

from decimal import Decimal

import pytest

from app.domain.rules.confidence import final_confidence, needs_review

D = Decimal


def test_final_confidence_is_the_lower_of_the_two_values():
    assert final_confidence(D("0.94"), D("0.60")) == D("0.60")


def test_final_confidence_when_the_ai_value_is_lower():
    assert final_confidence(D("0.55"), D("1")) == D("0.55")


def test_equal_values_give_that_value():
    assert final_confidence(D("0.80"), D("0.80")) == D("0.80")


def test_result_is_a_decimal_with_two_places():
    result = final_confidence(D("0.94"), D("0.6"))
    assert isinstance(result, Decimal)
    assert result.as_tuple().exponent == -2
    assert str(result) == "0.60"


def test_ratio_with_more_places_is_rounded_half_up_to_two_places():
    assert final_confidence(D("1"), D(2) / D(3)) == D("0.67")
    assert final_confidence(D("1"), D("0.935")) == D("0.94")
    assert final_confidence(D("1"), D("0.934")) == D("0.93")


@pytest.mark.parametrize("value", [D("0"), D("1")])
def test_limits_zero_and_one_are_accepted(value):
    assert final_confidence(value, value) == value


@pytest.mark.parametrize("bad", [D("-0.01"), D("1.01"), D("2")])
def test_values_outside_zero_to_one_are_refused_in_either_argument(bad):
    with pytest.raises(ValueError):
        final_confidence(bad, D("0.5"))
    with pytest.raises(ValueError):
        final_confidence(D("0.5"), bad)


def test_confidence_of_070_does_not_need_review():
    assert needs_review(D("0.70")) is False


def test_confidence_of_069_needs_review():
    assert needs_review(D("0.69")) is True


def test_confidence_above_070_does_not_need_review():
    assert needs_review(D("1")) is False


def test_review_check_also_refuses_values_outside_zero_to_one():
    with pytest.raises(ValueError):
        needs_review(D("1.5"))
