"""DUP-07: "Não é duplicada" restores a merged activity and marks the two as distinct."""

import uuid

import pytest

from app.application.services.activity_merge import MergeDuplicateActivities
from app.application.use_cases.scoring import DISTINCT_DEFAULT_TEXT
from app.domain.entities.audit import AuditAction
from app.domain.errors import NotFound, StaleVersion, ValidationFailed
from tests.integration.doc_usecases.merge_support import (
    documents,
    duplicate,
    load,
    merge_events,
    page_link,
    pages_of,
)


def merge(world):
    with world.uow_factory() as uow:
        MergeDuplicateActivities(world.audit).merge_process(uow, world.process.id, world.admin.id)
        uow.commit()


def separate(world, activity, expected_version=None):
    with world.uow_factory() as uow:
        restored = MergeDuplicateActivities(world.audit).separate(
            uow, world.admin.id, activity.id, expected_version
        )
        uow.commit()
    return restored


def visible(world):
    with world.uow_factory() as uow:
        return {a.id for a in uow.activities.list_for_process(world.process.id)}


@pytest.fixture
def merged_pair(world):
    older, newer = duplicate(world, 1), duplicate(world, 2)
    doc_a, doc_b, doc_c = documents(world, 3)
    page_link(world, older, doc_a, 1)
    page_link(world, newer, doc_b, 2)
    page_link(world, newer, doc_c, 3)
    merge(world)
    return older, newer, (doc_a, doc_b, doc_c)


def test_the_activity_goes_back_to_the_lists_with_the_evidences_that_came_from_it(
    world, merged_pair
):
    older, newer, (doc_a, doc_b, doc_c) = merged_pair
    assert visible(world) == {older.id}

    restored = separate(world, newer)

    assert (restored.id, restored.merged_into_id, restored.is_merged) == (newer.id, None, False)
    assert visible(world) == {older.id, newer.id}
    assert set(pages_of(world, newer)) == {(doc_b.id, 2), (doc_c.id, 3)}
    assert set(pages_of(world, older)) == {(doc_a.id, 1)}
    assert all(e.origin_activity_id is None for e in pages_of(world, newer).values())


def test_only_the_evidences_with_that_origin_come_back(world):
    kept = duplicate(world, 1)
    first, second = duplicate(world, 2), duplicate(world, 3)
    doc_a, doc_b = documents(world, 2)
    page_link(world, first, doc_a, 1)
    page_link(world, second, doc_b, 1)
    merge(world)

    separate(world, first)

    assert set(pages_of(world, first)) == {(doc_a.id, 1)}
    assert set(pages_of(world, kept)) == {(doc_b.id, 1)}
    assert pages_of(world, kept)[(doc_b.id, 1)].origin_activity_id == second.id
    assert load(world, second).merged_into_id == kept.id


def test_both_activities_are_marked_distinct_and_are_not_merged_again(world, merged_pair):
    older, newer, _ = merged_pair

    separate(world, newer)

    for activity in (older, newer):
        assert load(world, activity).distinct_justification == DISTINCT_DEFAULT_TEXT
    with world.uow_factory() as uow:
        report = MergeDuplicateActivities(world.audit).merge_process(
            uow, world.process.id, world.admin.id
        )
        uow.commit()
    assert report.count == 0
    assert visible(world) == {older.id, newer.id}


def test_a_justification_already_on_the_activities_is_kept(world):
    older = duplicate(world, 1, distinct_justification="Texto do docente")
    newer = duplicate(world, 2)
    merge(world)

    separate(world, newer)

    assert load(world, older).distinct_justification == "Texto do docente"


def test_only_a_merged_activity_can_be_separated(world, merged_pair):
    older, _, _ = merged_pair
    before = load(world, older)

    with pytest.raises(ValidationFailed) as error:
        separate(world, older)

    assert error.value.field == "atividade"
    assert load(world, older) == before


def test_an_unknown_activity_is_not_found(world):
    with world.uow_factory() as uow, pytest.raises(NotFound):
        MergeDuplicateActivities(world.audit).separate(uow, world.admin.id, uuid.uuid4(), None)


def test_a_stale_version_is_refused_and_nothing_changes(world, merged_pair):
    older, newer, _ = merged_pair
    current = load(world, newer)

    with pytest.raises(StaleVersion):
        separate(world, newer, expected_version=current.version - 1)

    assert load(world, newer) == current
    assert visible(world) == {older.id}


def test_the_current_version_is_accepted(world, merged_pair):
    _, newer, _ = merged_pair

    separate(world, newer, expected_version=load(world, newer).version)

    assert load(world, newer).merged_into_id is None


def test_the_separation_is_audited_with_both_ids(world, merged_pair):
    older, newer, _ = merged_pair

    separate(world, newer)

    with world.uow_factory() as uow:
        events = uow.audit.list_for("activity", str(newer.id))
    separation = [e for e in events if e.changes.get("operation", {}).get("after") == "SEPARATE"]
    assert len(separation) == 1
    [event] = separation
    assert event.action is AuditAction.UPDATE
    assert event.user_id == world.admin.id
    assert event.changes["merged_into_id"] == {"before": str(older.id), "after": None}
    assert event.changes["kept_activity_id"]["after"] == str(older.id)
    assert len(merge_events(world, newer)) == 2  # the merge event stays in the trail
