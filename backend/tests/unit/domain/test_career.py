"""CARR-01 (version selection by end date) and CARR-03 (minimum interstice)."""

from datetime import date

import pytest

from app.domain.entities.career import (
    CareerClass,
    CareerVersion,
    Modality,
    select_version,
)

OLD = CareerVersion(
    name="Antiga",
    valid_from=None,
    valid_to=date(2024, 12, 31),
    norm_reference="Res. antiga",
    classes=(
        CareerClass("A", ("Auxiliar",), (1, 2), None),
        CareerClass("B", ("Assistente",), (1, 2), 24),
        CareerClass("C", ("Adjunto",), (1, 2, 3, 4), 24),
    ),
)
NEW = CareerVersion(
    name="Nova",
    valid_from=date(2025, 1, 1),
    valid_to=None,
    norm_reference="Lei nova",
    classes=(
        CareerClass("A", ("Assistente",), (1,), None),
        CareerClass("B", ("Adjunto",), (1, 2, 3, 4), 36),
        CareerClass("C", ("Associado",), (1, 2, 3, 4), 24),
    ),
)


def test_select_version_end_date_31_12_2024_uses_old_structure():
    assert select_version([NEW, OLD], date(2024, 12, 31)) is OLD


def test_select_version_end_date_01_01_2025_uses_new_structure():
    assert select_version([OLD, NEW], date(2025, 1, 1)) is NEW


def test_select_version_returns_none_without_covering_version():
    future_only = CareerVersion("F", date(2030, 1, 1), None, "ref", ())
    assert select_version([future_only], date(2026, 11, 23)) is None
    assert select_version([], date(2026, 11, 23)) is None


def test_covers_boundaries():
    assert OLD.covers(date(2010, 1, 1)) is True
    assert OLD.covers(date(2025, 1, 1)) is False
    assert NEW.covers(date(2024, 12, 31)) is False
    assert NEW.covers(date(2099, 1, 1)) is True


def test_get_class_returns_class_or_none():
    assert OLD.get_class("C").denominations == ("Adjunto",)
    assert OLD.get_class("D") is None


def test_next_class_follows_structure_order():
    assert NEW.next_class("B").code == "C"
    assert NEW.next_class("C") is None
    assert NEW.next_class("Z") is None


def test_progression_min_months_is_24():
    assert OLD.min_months(Modality.PROGRESSAO, "C") == 24
    assert NEW.min_months(Modality.PROGRESSAO, "B") == 24


def test_promotion_min_months_comes_from_target_class():
    assert NEW.min_months(Modality.PROMOCAO, "B") == 36
    assert NEW.min_months(Modality.PROMOCAO, "C") == 24
    assert OLD.min_months(Modality.PROMOCAO, "B") == 24


@pytest.mark.parametrize("target", ["A", "Z"])
def test_promotion_min_months_undefined_for_entry_or_unknown_class(target):
    assert NEW.min_months(Modality.PROMOCAO, target) is None
