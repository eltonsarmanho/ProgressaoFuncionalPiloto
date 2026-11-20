"""TAB-01, TAB-02, TAB-06: scoring table entities."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

from app.domain.entities.scoring import (
    ScoringCriterion,
    ScoringGroup,
    ScoringMode,
    ScoringTableVersion,
    TableStatus,
    is_group1_load_criterion,
    is_pit_criterion,
)


def _criterion(group: int, item: int, **kwargs) -> ScoringCriterion:
    return ScoringCriterion(
        group_number=group,
        item_number=item,
        description=f"item {group}.{item}",
        unit_label="unidade",
        mode=kwargs.pop("mode", ScoringMode.POR_UNIDADE),
        unit_points=Decimal("10"),
        **kwargs,
    )


def _version(valid_from=date(2020, 1, 1), valid_to=date(2024, 12, 31), counts_group1=True):
    return ScoringTableVersion(
        table_id=None,
        name="Tabela de teste",
        valid_from=valid_from,
        valid_to=valid_to,
        norm_reference="Res. 4.644/2015-CONSEPE",
        status=TableStatus.OFICIAL,
        groups=(
            ScoringGroup(1, "Ensino", counts_in_total=counts_group1, criteria=(_criterion(1, 1),)),
            ScoringGroup(2, "Pesquisa", criteria=(_criterion(2, 7), _criterion(2, 8))),
        ),
    )


def test_get_criterion_returns_the_criterion_by_group_and_item():
    criterion = _version().get_criterion(2, 8)

    assert criterion is not None
    assert (criterion.group_number, criterion.item_number) == (2, 8)


def test_get_criterion_returns_none_for_unknown_item():
    assert _version().get_criterion(2, 99) is None


def test_get_criterion_returns_none_for_unknown_group():
    assert _version().get_criterion(7, 1) is None


def test_covers_is_inclusive_on_both_limits():
    version = _version(valid_from=date(2020, 1, 1), valid_to=date(2024, 12, 31))

    assert version.covers(date(2020, 1, 1)) is True
    assert version.covers(date(2024, 12, 31)) is True
    assert version.covers(date(2019, 12, 31)) is False
    assert version.covers(date(2025, 1, 1)) is False


def test_covers_open_ended_version_has_no_upper_limit():
    assert _version(valid_to=None).covers(date(2099, 1, 1)) is True


def test_group_that_does_not_count_in_total_is_representable():
    version = _version(counts_group1=False)

    assert version.get_group(1).counts_in_total is False
    assert version.get_group(2).counts_in_total is True


def test_criterion_keeps_mode_specific_fields_and_review_note():
    criterion = _criterion(
        1,
        1,
        mode=ScoringMode.CARGA_SEMANAL,
        weeks_per_semester=17,
        prep_ratio=Decimal("1"),
        review_note="difere do IFCH",
    )

    assert criterion.mode is ScoringMode.CARGA_SEMANAL
    assert criterion.weeks_per_semester == 17
    assert criterion.prep_ratio == Decimal("1")
    assert criterion.review_note == "difere do IFCH"


# --- minimum course hours (OFI-06) ----------------------------------------------------------


def test_criterion_min_hours_defaults_to_none():
    assert _criterion(4, 3).min_hours is None


def test_criterion_keeps_the_minimum_hours_it_is_given():
    assert _criterion(4, 4, min_hours=Decimal("20")).min_hours == Decimal("20")


def test_min_hours_does_not_change_equality_of_criteria_without_it():
    assert _criterion(4, 3) == _criterion(4, 3)
    assert _criterion(4, 3) != _criterion(4, 3, min_hours=Decimal("20"))


# --- group I load criterion and superseded version (GI-05, GI-07) ---------------------------


def _load_version(counts_group1: bool) -> ScoringTableVersion:
    return ScoringTableVersion(
        table_id=None,
        name="Tabela sintetica de teste",
        valid_from=date(2020, 1, 1),
        valid_to=None,
        norm_reference="Referencia sintetica",
        status=TableStatus.OFICIAL,
        groups=(
            ScoringGroup(
                1,
                "Ensino",
                counts_in_total=counts_group1,
                criteria=(
                    _criterion(1, 1, mode=ScoringMode.CARGA_SEMANAL, weeks_per_semester=17),
                    _criterion(1, 3),
                ),
            ),
            ScoringGroup(
                2,
                "Pesquisa",
                criteria=(_criterion(2, 1, mode=ScoringMode.CARGA_SEMANAL, weeks_per_semester=17),),
            ),
        ),
    )


def test_group1_weekly_load_criterion_is_a_load_criterion_with_the_group_outside_the_total():
    version = _load_version(counts_group1=False)

    assert is_group1_load_criterion(version.get_criterion(1, 1)) is True


def test_group1_weekly_load_criterion_is_a_load_criterion_with_the_group_inside_the_total():
    version = _load_version(counts_group1=True)

    assert is_group1_load_criterion(version.get_criterion(1, 1)) is True


def test_group1_per_unit_criterion_is_not_a_load_criterion():
    for counts in (False, True):
        assert is_group1_load_criterion(_load_version(counts).get_criterion(1, 3)) is False


def test_weekly_load_criterion_of_another_group_is_not_a_group1_load_criterion():
    for counts in (False, True):
        assert is_group1_load_criterion(_load_version(counts).get_criterion(2, 1)) is False


def test_pit_criterion_stays_true_only_with_the_group_outside_the_total():
    outside = _load_version(counts_group1=False)
    inside = _load_version(counts_group1=True)

    assert is_pit_criterion(outside, outside.get_criterion(1, 1)) is True
    assert is_pit_criterion(inside, inside.get_criterion(1, 1)) is False


def test_version_without_superseded_by_id_is_not_superseded():
    version = _load_version(counts_group1=True)

    assert version.superseded_by_id is None
    assert version.is_superseded is False


def test_version_with_superseded_by_id_is_superseded():
    version = _load_version(counts_group1=True)
    superseded = ScoringTableVersion(**{**version.__dict__, "superseded_by_id": uuid4()})

    assert superseded.is_superseded is True


def test_versions_that_differ_only_in_superseded_by_id_are_equal():
    version = _load_version(counts_group1=True)
    superseded = ScoringTableVersion(**{**version.__dict__, "superseded_by_id": uuid4()})

    assert superseded == version
