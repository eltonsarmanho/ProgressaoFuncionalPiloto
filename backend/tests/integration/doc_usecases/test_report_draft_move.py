"""REL-08: moving an activity to another section of the report draft."""

import uuid

import pytest

from app.domain.entities.generated import DocumentKind, GenerationCode
from app.domain.entities.process import ProcessStatus
from app.domain.entities.report import EntrySource
from app.domain.errors import Conflict, NotFound, StaleVersion, ValidationFailed
from tests.integration.doc_usecases.draft_support import (
    entries_by_section,
    get_draft_uc,
    move_uc,
    save_entry_uc,
    save_proposal,
    set_status,
    stored_draft,
)
from tests.integration.doc_usecases.generation_support import add_activity
from tests.integration.doc_usecases.test_run_generation_table import generate


def move(world, activity, section, version=0, actor=None):
    return move_uc(world).execute(
        actor or world.docente, world.process.id, activity.id, section, version
    )


def test_a_move_is_kept_in_the_draft_and_the_generation_uses_it(gen):
    world = gen.world
    moved = add_activity(world, title="Atividade para a seção 5")
    stays = add_activity(world, title="Atividade que fica", item_number=8)

    saved = move(world, moved, "5")

    assert saved.version == 1
    assert entries_by_section(stored_draft(world)) == {"1.3": [stays.id], "5": [moved.id]}
    view = get_draft_uc(world).execute(world.docente, world.process.id)
    assert entries_by_section(view.draft) == {"1.3": [stays.id], "5": [moved.id]}
    done = generate(gen, DocumentKind.RELATORIO)
    in_report = {
        s["key"]: [e["activity_id"] for e in s["entries"]]
        for s in done.snapshot["report"]["sections"]
    }
    assert in_report == {"1.3": [str(stays.id)], "5": [str(moved.id)]}


def test_a_move_in_a_saved_draft_raises_the_version_and_the_text_of_the_user_goes_with_it(
    official_chosen,
):
    world = official_chosen
    typed = add_activity(world, title="Com texto do docente")
    save_entry_uc(world).execute(world.docente, world.process.id, typed.id, "Texto do docente", 0)

    saved = move(world, typed, "2", version=1)

    assert saved.version == 2
    [entry] = [e for s in saved.sections if s.key == "2" for e in s.entries]
    assert (entry.activity_id, entry.text, entry.source) == (
        typed.id,
        "Texto do docente",
        EntrySource.USUARIO,
    )


def test_a_section_that_does_not_exist_is_a_422_and_nothing_is_saved(official_chosen):
    world = official_chosen
    activity = add_activity(world)

    with pytest.raises(ValidationFailed) as error:
        move(world, activity, "9.9")

    assert error.value.field == "section_key"
    assert stored_draft(world) is None


def test_an_outdated_version_is_a_409_and_the_draft_stays_as_it_was(official_chosen):
    world = official_chosen
    activity = add_activity(world)
    saved = save_proposal(world)

    with pytest.raises(StaleVersion) as error:
        move(world, activity, "5", version=0)

    assert error.value.code == GenerationCode.VERSAO_DESATUALIZADA
    assert stored_draft(world) == saved


def test_a_concluded_process_a_process_out_of_reach_and_an_unknown_activity_are_refused(
    official_chosen,
):
    world = official_chosen
    activity = add_activity(world)

    with pytest.raises(NotFound):
        move(world, activity, "5", actor=world.other_docente)
    with pytest.raises(NotFound):
        move_uc(world).execute(world.docente, world.process.id, uuid.uuid4(), "5", 0)
    set_status(world, ProcessStatus.CONCLUIDO)
    with pytest.raises(Conflict) as error:
        move(world, activity, "5")

    assert error.value.code == GenerationCode.PROCESSO_SOMENTE_LEITURA
    assert stored_draft(world) is None
