"""REL-01, REL-07, REL-11: reading the report draft."""

import uuid
from types import SimpleNamespace

import pytest

from app.domain.entities.activity import ActivityStatus
from app.domain.entities.generated import GenerationAlertCode
from app.domain.entities.report import EntrySource
from app.domain.errors import NotFound
from tests.integration.doc_usecases.draft_support import (
    entries_by_section,
    get_draft_uc,
    save_proposal,
    stored_draft,
)
from tests.integration.doc_usecases.generation_support import add_activity

ALL_SECTIONS = ("1.1", "1.2", "1.3", "2", "3", "4", "5", "6")


def reject(world, activity):
    with world.uow_factory() as uow:
        version = uow.activities.get(activity.id).version
    world.change_status.execute(world.admin, activity.id, ActivityStatus.REJEITADA, version, None)


def read(world, actor=None, process=None):
    return get_draft_uc(world).execute(actor or world.docente, (process or world.process).id)


def test_a_first_read_proposes_the_draft_without_saving_it_and_distributes_by_the_group_map(
    official_chosen,
):
    world = official_chosen
    orientation = add_activity(world, title="Orientação de TCC", group_number=2, item_number=7)
    extension = add_activity(world, title="Curso de extensão", group_number=4, item_number=1)

    first = read(world)
    second = read(world)

    for view in (first, second):
        assert (view.saved, view.draft.version) == (False, 0)
        assert entries_by_section(view.draft) == {
            "1.3": [orientation.id],
            "3": [extension.id],
        }
    assert stored_draft(world) is None
    assert [s.key for s in first.draft.sections] == list(ALL_SECTIONS)


def test_a_section_with_no_activity_is_listed_as_empty(official_chosen):
    world = official_chosen
    add_activity(world, group_number=4, item_number=1)

    view = read(world)

    assert view.empty_sections == ("1.1", "1.2", "1.3", "2", "4", "5", "6")


def test_an_activity_validated_after_the_last_save_goes_to_the_end_of_its_section_with_the_alert(
    official_chosen,
):
    world = official_chosen
    old = add_activity(world, title="Orientação antiga")
    save_proposal(world)
    new = add_activity(world, title="Orientação nova")

    view = read(world)

    assert (view.saved, view.draft.version) == (True, 1)
    section = next(s for s in view.draft.sections if s.key == "1.3")
    assert [e.activity_id for e in section.entries] == [old.id, new.id]
    assert [a.code for a in view.alerts] == [GenerationAlertCode.RASCUNHO_DESATUALIZADO]
    assert GenerationAlertCode.RASCUNHO_DESATUALIZADO in [w.code for w in section.warnings]
    assert [e.activity_id for s in stored_draft(world).sections for e in s.entries] == [old.id]


def test_an_activity_that_left_the_validated_ones_leaves_the_draft_with_the_alert(official_chosen):
    world = official_chosen
    stays = add_activity(world, title="Fica")
    leaves = add_activity(world, title="Sai")
    save_proposal(world)
    reject(world, leaves)

    view = read(world)

    assert entries_by_section(view.draft) == {"1.3": [stays.id]}
    assert [a.code for a in view.alerts] == [GenerationAlertCode.RASCUNHO_DESATUALIZADO]


def test_a_saved_draft_with_nothing_new_has_no_alert_and_keeps_the_text_of_the_user(
    official_chosen,
):
    world = official_chosen
    activity = add_activity(world)
    saved = save_proposal(world)

    view = read(world)

    assert view.alerts == ()
    assert view.draft == saved
    assert view.draft.sections[2].entries[0].source is EntrySource.MODELO
    assert view.draft.sections[2].entries[0].activity_id == activity.id


@pytest.mark.parametrize("actor", ["other_docente", "other_secretaria"])
def test_a_process_out_of_reach_is_not_found(official_chosen, actor):
    world = official_chosen
    add_activity(world)

    with pytest.raises(NotFound):
        read(world, actor=getattr(world, actor))


def test_an_unknown_process_is_not_found(official_chosen):
    world = official_chosen

    with pytest.raises(NotFound):
        read(world, process=SimpleNamespace(id=uuid.uuid4()))


def test_the_names_of_the_items_come_from_the_chosen_table(official_chosen):
    world = official_chosen
    add_activity(world, group_number=4, item_number=1)

    view = read(world)

    criterion = world.official_version.get_criterion(4, 1)
    assert view.item_names[(4, 1)] == criterion.description
