"""ATV-02, ATV-03, ATV-04: activity status and Group I item rules."""

import pytest

from app.domain.entities.activity import (
    ActivitySource,
    ActivityStatus,
    Level,
    group1_item,
    initial_status,
)


def test_manual_activity_starts_validated():
    assert initial_status(ActivitySource.MANUAL) is ActivityStatus.VALIDADA


@pytest.mark.parametrize("source", [ActivitySource.SUGERIDA_IA, ActivitySource.IMPORTADA])
def test_non_manual_activity_starts_awaiting_review(source):
    assert initial_status(source) is ActivityStatus.AGUARDANDO_REVISAO


def test_graduation_level_maps_to_item_1():
    assert group1_item(Level.GRADUACAO) == 1


def test_postgraduate_level_maps_to_item_2():
    assert group1_item(Level.POS_GRADUACAO) == 2


def test_stored_status_admits_only_the_three_spec_values():
    assert {s.value for s in ActivityStatus} == {"AGUARDANDO_REVISAO", "VALIDADA", "REJEITADA"}


def test_unknown_status_is_rejected():
    with pytest.raises(ValueError):
        ActivityStatus("POTENCIAL")
