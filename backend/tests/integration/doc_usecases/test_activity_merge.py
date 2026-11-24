"""DUP-01, DUP-02, DUP-03, DUP-05, DUP-06: merging the duplicate activities of a process."""

from dataclasses import replace
from datetime import date

import pytest

from app.application.services.activity_merge import MergeDuplicateActivities
from app.domain.entities.activity import ActivityStatus
from app.domain.entities.audit import AuditAction
from app.domain.entities.process import ProcessStatus
from tests.integration.doc_usecases.merge_support import (
    documents,
    duplicate,
    load,
    merge_events,
    page_link,
    pages_of,
)


def run(world, process=None):
    """Merges the process in one unit of work and commits, as the caller does."""
    process = process or world.process
    with world.uow_factory() as uow:
        report = MergeDuplicateActivities(world.audit).merge_process(
            uow, process.id, world.admin.id
        )
        uow.commit()
    return report


def visible(world, process=None):
    with world.uow_factory() as uow:
        return {a.id for a in uow.activities.list_for_process((process or world.process).id)}


def test_two_duplicates_become_one_with_the_evidences_of_both(world):
    older, newer = duplicate(world, 1), duplicate(world, 2)
    doc_a, doc_b, doc_c = documents(world, 3)
    page_link(world, older, doc_a, 1)
    page_link(world, older, doc_b, 2)
    page_link(world, newer, doc_b, 2)  # the same document and page as one the older has
    page_link(world, newer, doc_c, 5)

    report = run(world)

    assert report.count == 1
    assert visible(world) == {older.id}
    assert set(pages_of(world, older)) == {(doc_a.id, 1), (doc_b.id, 2), (doc_c.id, 5)}
    assert [e.origin_activity_id for k, e in pages_of(world, older).items() if k[1] == 5] == [
        newer.id
    ]


def test_the_merged_activity_stays_in_the_database_marked_with_the_kept_one(world):
    older, newer = duplicate(world, 1), duplicate(world, 2)

    run(world)

    merged = load(world, newer)
    assert (merged.merged_into_id, merged.is_merged, merged.title) == (
        older.id,
        True,
        newer.title,
    )
    assert load(world, older).merged_into_id is None
    with world.uow_factory() as uow:
        everything = uow.activities.list_for_process(world.process.id, include_merged=True)
    assert {a.id for a in everything} == {older.id, newer.id}


def test_the_validated_activity_stays_even_when_the_other_is_older(world):
    older = duplicate(world, 1)
    newer = duplicate(world, 2, status=ActivityStatus.VALIDADA)

    run(world)

    assert visible(world) == {newer.id}
    assert load(world, older).merged_into_id == newer.id


@pytest.mark.parametrize("status", [ActivityStatus.VALIDADA, ActivityStatus.AGUARDANDO_REVISAO])
def test_with_both_or_none_validated_the_one_created_first_stays(world, status):
    newer = duplicate(world, 5, status=status)
    older = duplicate(world, 3, status=status)

    run(world)

    assert visible(world) == {older.id}
    assert load(world, newer).merged_into_id == older.id


def test_with_several_validated_the_oldest_validated_stays(world):
    oldest = duplicate(world, 1)
    second = duplicate(world, 2, status=ActivityStatus.VALIDADA)
    third = duplicate(world, 3, status=ActivityStatus.VALIDADA)

    run(world)

    assert visible(world) == {second.id}
    assert {load(world, a).merged_into_id for a in (oldest, third)} == {second.id}


def _chain(world):
    """A touches B on 31/03 and B touches C on 30/06; A and C are apart: A~B, B~C."""
    spans = [
        (date(2023, 1, 1), date(2023, 3, 31)),
        (date(2023, 3, 31), date(2023, 6, 30)),
        (date(2023, 6, 30), date(2023, 9, 30)),
    ]
    return [
        duplicate(world, day, title="Orientação", event_date=None, period_start=a, period_end=b)
        for day, (a, b) in enumerate(spans, start=1)
    ]


def test_a_chain_of_three_becomes_one_activity(world):
    a, b, c = _chain(world)
    doc_a, doc_b, doc_c = documents(world, 3)
    for activity, document in ((a, doc_a), (b, doc_b), (c, doc_c)):
        page_link(world, activity, document)

    report = run(world)

    assert report.count == 2
    assert visible(world) == {a.id}
    assert {load(world, x).merged_into_id for x in (b, c)} == {a.id}
    assert set(pages_of(world, a)) == {(doc_a.id, 1), (doc_b.id, 1), (doc_c.id, 1)}


def test_merging_records_one_audit_event_with_both_ids(world):
    older, newer = duplicate(world, 1), duplicate(world, 2)

    run(world)

    [event] = merge_events(world, newer)
    assert event.action is AuditAction.UPDATE
    assert event.user_id == world.admin.id
    assert event.changes["operation"]["after"] == "MERGE"
    assert event.changes["merged_activity_id"]["after"] == str(newer.id)
    assert event.changes["kept_activity_id"]["after"] == str(older.id)
    assert event.changes["merged_into_id"]["after"] == str(older.id)
    assert merge_events(world, older) == []


def test_repeating_the_merge_changes_nothing(world):
    older, newer = duplicate(world, 1), duplicate(world, 2)
    page_link(world, newer, documents(world, 1)[0])
    run(world)
    snapshot = (load(world, older), load(world, newer), pages_of(world, older))

    again = run(world)

    assert again.count == 0
    assert (load(world, older), load(world, newer), pages_of(world, older)) == snapshot
    assert len(merge_events(world, newer)) == 1


def test_a_failure_in_the_middle_leaves_no_activity_nor_evidence_changed(world):
    a, b, c = _chain(world)
    for activity in (a, b, c):
        page_link(world, activity, documents(world, 1)[0])
    before = [(load(world, x), pages_of(world, x)) for x in (a, b, c)]

    with world.uow_factory() as uow:
        real_move = uow.evidences.move
        calls = []

        def failing_move(*args, **kwargs):
            calls.append(args)
            if len(calls) == 2:
                raise RuntimeError("falha forçada")
            return real_move(*args, **kwargs)

        uow.evidences.move = failing_move
        with pytest.raises(RuntimeError):
            MergeDuplicateActivities(world.audit).merge_process(uow, world.process.id, None)
    assert len(calls) == 2

    assert [(load(world, x), pages_of(world, x)) for x in (a, b, c)] == before
    assert visible(world) == {a.id, b.id, c.id}
    assert merge_events(world, b) == [] and merge_events(world, c) == []


def test_without_a_commit_by_the_caller_nothing_is_kept(world):
    older, newer = duplicate(world, 1), duplicate(world, 2)

    with world.uow_factory() as uow:
        report = MergeDuplicateActivities(world.audit).merge_process(
            uow, world.process.id, world.admin.id
        )
        assert report.count == 1

    assert visible(world) == {older.id, newer.id}


@pytest.mark.parametrize("status", [ProcessStatus.CONCLUIDO, ProcessStatus.ARQUIVADO])
def test_a_read_only_process_is_not_changed(world, status):
    older, newer = duplicate(world, 1), duplicate(world, 2)
    page_link(world, newer, documents(world, 1)[0])
    with world.uow_factory() as uow:
        current = uow.processes.get(world.process.id)
        uow.processes.update(replace(current, status=status), current.version)
        uow.commit()
    before = (load(world, older), load(world, newer), pages_of(world, older))

    report = run(world)

    assert report.count == 0
    assert (load(world, older), load(world, newer), pages_of(world, older)) == before
    assert merge_events(world, newer) == []


def test_activities_that_are_not_duplicates_are_left_alone(world):
    a = duplicate(world, 1)
    b = duplicate(world, 2, title="Outra atividade completamente diferente")
    released = duplicate(world, 3, distinct_justification="Outra oferta")

    assert run(world).count == 0
    assert visible(world) == {a.id, b.id, released.id}


def test_another_process_is_not_touched(world):
    other_a = duplicate(world, 1, process=world.ifch_process)
    other_b = duplicate(world, 2, process=world.ifch_process)
    duplicate(world, 1)
    duplicate(world, 2)

    assert run(world).count == 1

    assert visible(world, world.ifch_process) == {other_a.id, other_b.id}


def test_a_kept_activity_merged_later_takes_along_what_was_merged_into_it(world):
    kept = duplicate(world, 5)
    merged = duplicate(world, 6)
    doc = documents(world, 1)[0]
    page_link(world, merged, doc, 4)
    run(world)  # merged is now inside kept
    earlier = duplicate(world, 2)  # created before kept: it must now be the one that stays

    report = run(world)

    assert report.count == 1
    assert visible(world) == {earlier.id}
    assert load(world, kept).merged_into_id == earlier.id
    assert load(world, merged).merged_into_id == earlier.id
    assert pages_of(world, earlier)[(doc.id, 4)].origin_activity_id == merged.id
