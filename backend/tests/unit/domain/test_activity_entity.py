"""ATV-02, ATV-03, ATV-04: activity status and Group I item rules."""

import uuid
from dataclasses import replace

import pytest

from app.domain.entities.activity import (
    Activity,
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


def _activity(**kwargs) -> Activity:
    return Activity(
        id=uuid.uuid4(), process_id=uuid.uuid4(), title="Aula", created_by=uuid.uuid4(), **kwargs
    )


def test_an_activity_is_not_merged_by_default():
    activity = _activity()

    assert activity.merged_into_id is None
    assert activity.is_merged is False


def test_an_activity_is_merged_only_when_merged_into_id_is_set():
    kept_id = uuid.uuid4()

    activity = _activity(merged_into_id=kept_id)

    assert activity.merged_into_id == kept_id
    assert activity.is_merged is True


def test_replace_keeps_the_merged_into_id_and_clearing_it_unmerges():
    kept_id = uuid.uuid4()
    merged = _activity(merged_into_id=kept_id)

    renamed = replace(merged, title="Outro")

    assert (renamed.merged_into_id, renamed.is_merged) == (kept_id, True)
    assert replace(merged, merged_into_id=None).is_merged is False
