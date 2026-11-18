"""ARR-01, ARR-08, CMP-04: reading the arrangement of the Comprovante."""

import dataclasses

import pytest

from app.domain.entities.activity import ActivityStatus
from app.domain.entities.comprovante import EvidenceKey, TocLevel
from app.domain.entities.generated import GenerationAlertCode
from app.domain.errors import NotFound
from tests.integration.doc_usecases.draft_support import get_layout_uc, save_current_layout
from tests.integration.doc_usecases.generation_support import (
    MOMENT,
    add_activity,
    add_document,
    link,
)


def read(world, actor=None):
    return get_layout_uc(world).execute(actor or world.docente, world.process.id)


def stored(world):
    with world.uow_factory() as uow:
        return uow.comprovante_layouts.get(world.process.id)


def pages_of(view, activity):
    entry = next(a for a in view.layout.activities if a.activity_id == activity.id)
    return [(p.document_id, p.page) for p in entry.pages]


def test_without_a_saved_arrangement_it_is_built_from_the_links_in_the_order_of_the_table(
    official_chosen,
):
    world = official_chosen
    late = add_activity(world, title="Banca", group_number=3, item_number=2)
    first = add_activity(world, title="Orientação", item_number=7)
    document = add_document(world, page_count=5)
    link(world, first, document, 2)
    link(world, first, document, 1)
    link(world, late, document, 4)

    view = read(world)

    assert (view.saved, view.layout.version) == (False, 0)
    assert [a.activity_id for a in view.layout.activities] == [first.id, late.id]
    assert pages_of(view, first) == [(document.id, 2), (document.id, 1)]
    assert pages_of(view, late) == [(document.id, 4)]
    assert not view.stale and view.alerts == ()
    assert view.invalid == ()


def test_the_plan_gives_the_numbers_the_comprovante_will_have(official_chosen):
    world = official_chosen
    first = add_activity(world, title="Orientação", item_number=7)
    second = add_activity(world, title="Outra orientação", item_number=8)
    document = add_document(world, page_count=5)
    link(world, first, document, 3)
    link(world, second, document, 5)

    view = read(world)

    # cover 1, table of contents 2, separator of the group 3, then the original pages
    numbers = {
        e.activity_id: (e.first_page, e.last_page)
        for e in view.plan.toc
        if e.level is TocLevel.ATIVIDADE
    }
    assert numbers == {first.id: (4, 4), second.id: (5, 5)}
    assert [(p.document_id, p.source_page, p.number) for p in view.plan.pages if p.document_id] == [
        (document.id, 3, 4),
        (document.id, 5, 5),
    ]
    assert view.plan.plan_hash


def test_a_read_never_writes_the_arrangement(official_chosen):
    world = official_chosen
    activity = add_activity(world)
    link(world, activity, add_document(world), 1)

    read(world)
    read(world)

    assert stored(world) is None


def test_a_saved_arrangement_is_shown_with_its_version_and_no_alert_while_nothing_changed(
    official_chosen,
):
    world = official_chosen
    activity = add_activity(world)
    link(world, activity, add_document(world), 1)
    save_current_layout(world)

    view = read(world)

    assert (view.saved, view.layout.version) == (True, 1)
    assert not view.stale and view.alerts == ()


def _reject(world, activity):
    with world.uow_factory() as uow:
        current = uow.activities.get(activity.id)
        uow.activities.update(
            dataclasses.replace(current, status=ActivityStatus.REJEITADA), current.version
        )
        uow.commit()


def _move_item(world, activity):
    with world.uow_factory() as uow:
        current = uow.activities.get(activity.id)
        uow.activities.update(dataclasses.replace(current, item_number=8), current.version)
        uow.commit()


def _validate_another(world, activity):
    add_activity(world, title="Validada depois")


@pytest.mark.parametrize(
    ("change", "bucket"),
    [
        (_reject, "left_activity_ids"),
        (_move_item, "moved_activity_ids"),
        (_validate_another, "joined_activity_ids"),
    ],
    ids=["rejected", "moved-item", "validated-later"],
)
def test_an_activity_that_changed_after_the_save_makes_the_arrangement_stale_with_the_alert(
    official_chosen, change, bucket
):
    world = official_chosen
    activity = add_activity(world)
    link(world, activity, add_document(world), 1)
    save_current_layout(world)

    change(world, activity)
    view = read(world)

    assert view.stale is True
    assert [a.code for a in view.alerts] == [GenerationAlertCode.ARRANJO_DESATUALIZADO]
    assert getattr(view.staleness, bucket)


def test_a_page_linked_after_the_save_makes_the_arrangement_stale(official_chosen):
    world = official_chosen
    activity = add_activity(world)
    document = add_document(world, page_count=3)
    link(world, activity, document, 1)
    save_current_layout(world)

    link(world, activity, document, 2)
    view = read(world)

    assert view.stale is True
    assert view.staleness.new_link_activity_ids == (activity.id,)


def test_a_document_deleted_after_the_save_shows_as_an_invalid_entry(official_chosen):
    world = official_chosen
    activity = add_activity(world)
    kept = add_document(world, page_count=2)
    gone = add_document(world, page_count=2)
    link(world, activity, kept, 1)
    link(world, activity, gone, 2)
    save_current_layout(world)
    with world.uow_factory() as uow:
        uow.documents.delete(gone.id)
        uow.commit()

    view = read(world)

    assert view.invalid == (EvidenceKey(activity.id, gone.id, 2),)
    assert (gone.id, 2) in pages_of(view, activity)  # kept, so the user sees it and removes it


def test_a_document_whose_file_was_deleted_shows_as_an_invalid_entry(official_chosen):
    world = official_chosen
    activity = add_activity(world)
    document = add_document(world, page_count=2)
    link(world, activity, document, 1)
    save_current_layout(world)
    with world.uow_factory() as uow:
        uow.documents.mark_file_deleted(document.id, MOMENT)
        uow.commit()

    assert read(world).invalid == (EvidenceKey(activity.id, document.id, 1),)


def test_pages_of_a_document_outside_the_interstice_are_not_in_the_arrangement(official_chosen):
    world = official_chosen
    activity = add_activity(world)
    inside = add_document(world)
    outside = add_document(world, outside=True)
    link(world, activity, inside, 1)
    link(world, activity, outside, 1)

    derived = read(world)
    save_current_layout(world)
    with world.uow_factory() as uow:  # a saved arrangement that still carries the outside page
        saved = uow.comprovante_layouts.get(world.process.id)
        page = dataclasses.replace(saved.activities[0].pages[0], document_id=outside.id)
        with_outside = dataclasses.replace(
            saved,
            activities=(
                dataclasses.replace(saved.activities[0], pages=(*saved.activities[0].pages, page)),
            ),
        )
        uow.comprovante_layouts.update(with_outside, world.admin.id, 1)
        uow.commit()
    saved_view = read(world)

    for view in (derived, saved_view):
        assert pages_of(view, activity) == [(inside.id, 1)]
        assert view.invalid == ()
        assert outside.id not in {p.document_id for p in view.plan.pages if p.document_id}


def test_a_process_out_of_reach_is_not_found(official_chosen):
    world = official_chosen
    add_activity(world)

    with pytest.raises(NotFound):
        read(world, actor=world.other_docente)
