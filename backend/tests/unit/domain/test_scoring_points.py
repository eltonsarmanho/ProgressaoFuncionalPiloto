"""CALC-02..CALC-06 and the hour-block edge case."""

from decimal import Decimal
from uuid import uuid4

from app.domain.entities.activity import Activity
from app.domain.entities.scoring import ScoringCriterion, ScoringMode
from app.domain.rules.scoring_points import criterion_points

D = Decimal


def _activity(**kwargs) -> Activity:
    return Activity(id=uuid4(), process_id=uuid4(), title="Atividade", created_by=uuid4(), **kwargs)


def _criterion(mode: ScoringMode, **kwargs) -> ScoringCriterion:
    return ScoringCriterion(
        group_number=2, item_number=7, description="d", unit_label="u", mode=mode, **kwargs
    )


def _weekly(prep: str = "1", **kwargs) -> ScoringCriterion:
    return _criterion(
        ScoringMode.CARGA_SEMANAL, weeks_per_semester=17, prep_ratio=D(prep), **kwargs
    )


def _blocks() -> ScoringCriterion:
    return _criterion(ScoringMode.POR_BLOCO_DE_HORAS, unit_points=D("5"), hours_per_block=D("3"))


def test_per_unit_four_times_ten_is_forty():
    criterion = _criterion(ScoringMode.POR_UNIDADE, unit_points=D("10"))

    result = criterion_points(criterion, _activity(quantity=D("4")))

    assert result.points == D("40")
    assert result.effective_quantity == D("4")
    assert result.formula_text == "4 × 10"
    assert result.overridden is False


def test_per_block_21_hours_in_blocks_of_3_with_5_points_is_35():
    result = criterion_points(_blocks(), _activity(hours=D("21")))

    assert result.points == D("35")
    assert result.effective_quantity == D("7")


def test_per_block_2_hours_gives_zero_blocks_and_zero_points():
    result = criterion_points(_blocks(), _activity(hours=D("2")))

    assert result.points == D("0")
    assert result.effective_quantity == D("0")


def test_per_block_22_hours_discards_the_remainder_giving_7_blocks():
    result = criterion_points(_blocks(), _activity(hours=D("22")))

    assert result.effective_quantity == D("7")
    assert result.points == D("35")


def test_weekly_load_68_hours_graduation_is_8():
    assert criterion_points(_weekly("1"), _activity(hours=D("68"))).points == D("8.00")


def test_weekly_load_34_hours_graduation_is_4():
    assert criterion_points(_weekly("1"), _activity(hours=D("34"))).points == D("4.00")


def test_weekly_load_68_hours_postgraduate_is_12():
    assert criterion_points(_weekly("2"), _activity(hours=D("68"))).points == D("12.00")


def test_weekly_load_20_hours_graduation_rounds_half_up_to_2_35():
    result = criterion_points(_weekly("1"), _activity(hours=D("20")))

    assert result.points == D("2.35")
    assert result.points.as_tuple().exponent == -2


def test_weekly_load_rounds_half_up_not_half_even():
    # 1 h / 8 weeks = 0.125, a true tie: half up gives 0.13 (half even would give 0.12)
    criterion = _criterion(ScoringMode.CARGA_SEMANAL, weeks_per_semester=8, prep_ratio=D("0"))

    assert criterion_points(criterion, _activity(hours=D("1"))).points == D("0.13")


def test_weekly_load_override_replaces_the_calculation_and_marks_the_adjustment():
    result = criterion_points(_weekly("1"), _activity(hours=D("20"), points_override=D("24")))

    assert result.points == D("24")
    assert result.overridden is True


def test_weekly_load_without_override_is_not_marked_as_adjusted():
    assert criterion_points(_weekly("1"), _activity(hours=D("68"))).overridden is False


def test_informed_value_below_the_cap_is_kept():
    criterion = _criterion(ScoringMode.VALOR_INFORMADO, max_points=D("10"))

    result = criterion_points(criterion, _activity(informed_points=D("7")))

    assert result.points == D("7")
    assert result.limited_from is None


def test_informed_value_above_the_cap_is_limited_to_the_maximum():
    criterion = _criterion(ScoringMode.VALOR_INFORMADO, max_points=D("10"))

    result = criterion_points(criterion, _activity(informed_points=D("14")))

    assert result.points == D("10")
    assert result.limited_from == D("14")


def test_override_does_not_apply_outside_weekly_load_mode():
    criterion = _criterion(ScoringMode.POR_UNIDADE, unit_points=D("10"))

    result = criterion_points(criterion, _activity(quantity=D("2"), points_override=D("99")))

    assert result.points == D("20")
    assert result.overridden is False
