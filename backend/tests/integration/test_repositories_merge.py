"""DUP-01, DUP-02, DUP-03, DUP-07: listing, merging and restoring activities and their
evidences on real PostgreSQL."""

import uuid
from datetime import UTC, datetime

import pytest

from app.domain.errors import StaleVersion
from app.domain.repositories.ports import ActivityEvidence
from tests.integration.documents.factories import make_document
from tests.integration.test_scoring_repositories import (  # noqa: F401  (fixture and helpers)
    add_process,
    base,
    make_activity,
)


@pytest.fixture
def process(uow_factory, base):  # noqa: F811
    return add_process(uow_factory, base)


def _add(uow_factory, process, base, created, **kwargs):  # noqa: F811
    activity = make_activity(
        process,
        base,
        candidates=(),
        created_at=datetime(2025, 1, created, tzinfo=UTC),
        **kwargs,
    )
    with uow_factory() as uow:
        uow.activities.add(activity)
        uow.commit()
    return activity


def _documents(uow_factory, process, base, count):  # noqa: F811
    documents = [make_document(process, base["admin"].id) for _ in range(count)]
    with uow_factory() as uow:
        for document in documents:
            uow.documents.add(document)
        uow.commit()
    return documents


def _link(uow_factory, base, activity, document, page=1, **kwargs):  # noqa: F811
    evidence = ActivityEvidence(
        id=uuid.uuid4(),
        activity_id=activity.id,
        document_id=document.id,
        page_number=page,
        excerpt="trecho",
        created_by=base["admin"].id,
        **kwargs,
    )
    with uow_factory() as uow:
        uow.evidences.add(evidence)
        uow.commit()
    return evidence


def _merge(uow_factory, merged, kept):
    with uow_factory() as uow:
        current = uow.activities.get(merged.id)
        uow.activities.set_merged_into(current, kept.id, current.version)
        uow.commit()


def _evidences(uow_factory, activity):
    with uow_factory() as uow:
        found = uow.evidences.list_for_activity(activity.id)
    return {(e.document_id, e.page_number): e for e in found}


# --- listing (DUP-03) ----------------------------------------------------------------------


def test_the_default_list_leaves_the_merged_activities_out(uow_factory, base, process):  # noqa: F811
    kept = _add(uow_factory, process, base, 1, title="Mantida")
    merged = _add(uow_factory, process, base, 2, title="Mesclada")
    _merge(uow_factory, merged, kept)

    with uow_factory() as uow:
        default = uow.activities.list_for_process(process.id)
        with_merged = uow.activities.list_for_process(process.id, include_merged=True)
        filtered = uow.activities.list_for_process(process.id, group_number=1)

    assert [a.title for a in default] == ["Mantida"]
    assert [a.title for a in with_merged] == ["Mantida", "Mesclada"]
    assert [a.title for a in filtered] == ["Mantida"]


def test_list_merged_into_returns_only_the_ones_merged_into_that_activity(
    uow_factory, base, process  # noqa: F811
):
    kept = _add(uow_factory, process, base, 1, title="Mantida")
    other = _add(uow_factory, process, base, 2, title="Outra")
    second = _add(uow_factory, process, base, 4, title="Segunda mesclada")
    first = _add(uow_factory, process, base, 3, title="Primeira mesclada")
    stray = _add(uow_factory, process, base, 5, title="Mesclada na outra")
    for merged in (second, first):
        _merge(uow_factory, merged, kept)
    _merge(uow_factory, stray, other)

    with uow_factory() as uow:
        merged_into_kept = uow.activities.list_merged_into(kept.id)
        none = uow.activities.list_merged_into(uuid.uuid4())

    assert [a.title for a in merged_into_kept] == ["Primeira mesclada", "Segunda mesclada"]
    assert none == []


# --- set_merged_into (DUP-02) --------------------------------------------------------------


def test_set_merged_into_stores_the_target_and_bumps_the_version(uow_factory, base, process):  # noqa: F811
    kept = _add(uow_factory, process, base, 1, title="Mantida")
    merged = _add(uow_factory, process, base, 2, title="Mesclada")

    with uow_factory() as uow:
        current = uow.activities.get(merged.id)
        uow.activities.set_merged_into(current, kept.id, 1)
        assert (current.merged_into_id, current.version) == (kept.id, 2)
        uow.commit()
    with uow_factory() as uow:
        loaded = uow.activities.get(merged.id)

    assert (loaded.merged_into_id, loaded.is_merged, loaded.version) == (kept.id, True, 2)
    assert loaded.title == "Mesclada"


def test_set_merged_into_with_a_stale_version_changes_nothing(uow_factory, base, process):  # noqa: F811
    kept = _add(uow_factory, process, base, 1, title="Mantida")
    merged = _add(uow_factory, process, base, 2, title="Mesclada")
    with uow_factory() as uow:
        current = uow.activities.get(merged.id)
        uow.activities.update(current, 1)  # version 2 now
        uow.commit()

    with uow_factory() as uow:
        stale = uow.activities.get(merged.id)
        with pytest.raises(StaleVersion):
            uow.activities.set_merged_into(stale, kept.id, 1)
    with uow_factory() as uow:
        assert uow.activities.get(merged.id).merged_into_id is None


def test_set_merged_into_none_unmerges_the_activity(uow_factory, base, process):  # noqa: F811
    kept = _add(uow_factory, process, base, 1, title="Mantida")
    merged = _add(uow_factory, process, base, 2, title="Mesclada")
    _merge(uow_factory, merged, kept)

    with uow_factory() as uow:
        current = uow.activities.get(merged.id)
        uow.activities.set_merged_into(current, None, current.version)
        uow.commit()
    with uow_factory() as uow:
        loaded = uow.activities.get(merged.id)
        listed = uow.activities.list_for_process(process.id)

    assert (loaded.merged_into_id, loaded.is_merged) == (None, False)
    assert [a.title for a in listed] == ["Mantida", "Mesclada"]


def test_an_update_of_a_merged_activity_keeps_its_merged_into_id(uow_factory, base, process):  # noqa: F811
    kept = _add(uow_factory, process, base, 1, title="Mantida")
    merged = _add(uow_factory, process, base, 2, title="Mesclada")
    _merge(uow_factory, merged, kept)

    with uow_factory() as uow:
        current = uow.activities.get(merged.id)
        current.title = "Editada"
        uow.activities.update(current, current.version)
        uow.commit()
    with uow_factory() as uow:
        assert uow.activities.get(merged.id).merged_into_id == kept.id


# --- moving and restoring evidences --------------------------------------------------------


def test_move_gives_the_evidences_to_the_target_and_records_where_they_came_from(
    uow_factory, base, process  # noqa: F811
):
    kept = _add(uow_factory, process, base, 1, title="Mantida")
    merged = _add(uow_factory, process, base, 2, title="Mesclada")
    doc_a, doc_b = _documents(uow_factory, process, base, 2)
    own = _link(uow_factory, base, kept, doc_a, page=1)
    first = _link(uow_factory, base, merged, doc_b, page=3)
    second = _link(uow_factory, base, merged, doc_b, page=4)

    with uow_factory() as uow:
        moved = uow.evidences.move([first.id, second.id], kept.id, merged.id)
        uow.commit()

    assert sorted(moved) == sorted([first.id, second.id])
    on_kept = _evidences(uow_factory, kept)
    assert set(on_kept) == {(doc_a.id, 1), (doc_b.id, 3), (doc_b.id, 4)}
    assert on_kept[(doc_a.id, 1)].origin_activity_id is None
    assert on_kept[(doc_b.id, 3)].origin_activity_id == merged.id
    assert on_kept[(doc_b.id, 4)].origin_activity_id == merged.id
    assert on_kept[(doc_b.id, 3)].id == first.id
    assert own.id == on_kept[(doc_a.id, 1)].id
    assert _evidences(uow_factory, merged) == {}


def test_move_does_not_repeat_a_document_and_page_the_target_already_has(
    uow_factory, base, process  # noqa: F811
):
    kept = _add(uow_factory, process, base, 1, title="Mantida")
    merged = _add(uow_factory, process, base, 2, title="Mesclada")
    doc_a, doc_b = _documents(uow_factory, process, base, 2)
    _link(uow_factory, base, kept, doc_a, page=1)
    repeated = _link(uow_factory, base, merged, doc_a, page=1)
    new = _link(uow_factory, base, merged, doc_b, page=2)

    with uow_factory() as uow:
        moved = uow.evidences.move([repeated.id, new.id], kept.id, merged.id)
        uow.commit()

    assert moved == [new.id]
    assert set(_evidences(uow_factory, kept)) == {(doc_a.id, 1), (doc_b.id, 2)}
    assert set(_evidences(uow_factory, merged)) == {(doc_a.id, 1)}


def test_move_of_the_same_page_from_two_activities_moves_it_only_once(
    uow_factory, base, process  # noqa: F811
):
    kept = _add(uow_factory, process, base, 1, title="Mantida")
    first = _add(uow_factory, process, base, 2, title="Primeira")
    second = _add(uow_factory, process, base, 3, title="Segunda")
    [doc] = _documents(uow_factory, process, base, 1)
    from_first = _link(uow_factory, base, first, doc, page=7)
    from_second = _link(uow_factory, base, second, doc, page=7)

    with uow_factory() as uow:
        moved_first = uow.evidences.move([from_first.id], kept.id, first.id)
        moved_second = uow.evidences.move([from_second.id], kept.id, second.id)
        uow.commit()

    assert (moved_first, moved_second) == ([from_first.id], [])
    assert set(_evidences(uow_factory, kept)) == {(doc.id, 7)}
    assert set(_evidences(uow_factory, second)) == {(doc.id, 7)}


def test_move_keeps_the_origin_a_link_already_had(uow_factory, base, process):  # noqa: F811
    kept = _add(uow_factory, process, base, 1, title="Mantida")
    middle = _add(uow_factory, process, base, 2, title="Do meio")
    newest = _add(uow_factory, process, base, 3, title="Nova")
    [doc] = _documents(uow_factory, process, base, 1)
    link = _link(uow_factory, base, middle, doc, page=1, origin_activity_id=newest.id)

    with uow_factory() as uow:
        uow.evidences.move([link.id], kept.id, middle.id)
        uow.commit()

    assert _evidences(uow_factory, kept)[(doc.id, 1)].origin_activity_id == newest.id


def test_restore_from_gives_back_only_the_links_that_came_from_that_activity(
    uow_factory, base, process  # noqa: F811
):
    kept = _add(uow_factory, process, base, 1, title="Mantida")
    merged = _add(uow_factory, process, base, 2, title="Mesclada")
    other = _add(uow_factory, process, base, 3, title="Outra mesclada")
    doc_a, doc_b, doc_c = _documents(uow_factory, process, base, 3)
    own = _link(uow_factory, base, kept, doc_a, page=1)
    from_merged = _link(uow_factory, base, merged, doc_b, page=2)
    from_other = _link(uow_factory, base, other, doc_c, page=3)
    with uow_factory() as uow:
        uow.evidences.move([from_merged.id], kept.id, merged.id)
        uow.evidences.move([from_other.id], kept.id, other.id)
        uow.commit()

    with uow_factory() as uow:
        restored = uow.evidences.restore_from(merged.id)
        uow.commit()

    assert restored == [from_merged.id]
    assert set(_evidences(uow_factory, kept)) == {(doc_a.id, 1), (doc_c.id, 3)}
    back = _evidences(uow_factory, merged)
    assert set(back) == {(doc_b.id, 2)}
    assert back[(doc_b.id, 2)].origin_activity_id is None
    assert _evidences(uow_factory, kept)[(doc_c.id, 3)].origin_activity_id == other.id
    assert _evidences(uow_factory, kept)[(doc_a.id, 1)].id == own.id


def test_restore_from_an_activity_with_nothing_to_give_back_returns_nothing(
    uow_factory, base, process  # noqa: F811
):
    activity = _add(uow_factory, process, base, 1, title="A")

    with uow_factory() as uow:
        assert uow.evidences.restore_from(activity.id) == []


# --- documents counts (DUP-03) -------------------------------------------------------------


def test_a_merged_activity_does_not_count_as_citing_the_document(uow_factory, base, process):  # noqa: F811
    kept = _add(uow_factory, process, base, 1, title="Mantida")
    merged = _add(uow_factory, process, base, 2, title="Mesclada")
    [doc] = _documents(uow_factory, process, base, 1)
    _link(uow_factory, base, kept, doc, page=1)
    _link(uow_factory, base, merged, doc, page=1)  # the same page: it stays on the merged one
    with uow_factory() as uow:
        assert uow.evidences.counts_for_documents([doc.id]) == {doc.id: 2}

    _merge(uow_factory, merged, kept)

    with uow_factory() as uow:
        assert uow.evidences.counts_for_documents([doc.id]) == {doc.id: 1}
