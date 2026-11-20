"""REL-07, REL-11: saving the text of the report draft."""

import uuid

import pytest

from app.domain.entities.audit import AuditAction
from app.domain.entities.generated import GenerationCode
from app.domain.entities.process import ProcessStatus
from app.domain.entities.report import EntrySource
from app.domain.errors import Conflict, NotFound, StaleVersion, ValidationFailed
from tests.integration.doc_usecases.draft_support import (
    get_draft_uc,
    save_entry_uc,
    save_proposal,
    save_section_uc,
    set_status,
    stored_draft,
)
from tests.integration.doc_usecases.generation_support import add_activity

TEXT = "Orientação concluída, texto escrito pelo usuário."


def entry_of(draft, activity):
    return next(e for s in draft.sections for e in s.entries if e.activity_id == activity.id)


def section_of(draft, key):
    return next(s for s in draft.sections if s.key == key)


def save_entry(world, activity, text=TEXT, version=0, actor=None):
    return save_entry_uc(world).execute(
        actor or world.docente, world.process.id, activity.id, text, version
    )


def test_the_first_save_expects_version_0_creates_the_draft_and_keeps_the_text_as_the_users(
    official_chosen,
):
    world = official_chosen
    edited = add_activity(world, title="Orientação editada")
    other = add_activity(world, title="Orientação do modelo")

    saved = save_entry(world, edited)

    assert saved.version == 1
    stored = stored_draft(world)
    assert stored == saved
    assert (entry_of(stored, edited).text, entry_of(stored, edited).source) == (
        TEXT,
        EntrySource.USUARIO,
    )
    assert entry_of(stored, other).source is EntrySource.MODELO
    assert "Orientação do modelo" in entry_of(stored, other).text


def test_the_edited_text_stays_after_a_new_read_even_when_an_activity_arrives(official_chosen):
    world = official_chosen
    edited = add_activity(world, title="Orientação editada")
    save_entry(world, edited)
    add_activity(world, title="Chegou depois")

    view = get_draft_uc(world).execute(world.docente, world.process.id)

    found = entry_of(view.draft, edited)
    assert (found.text, found.source) == (TEXT, EntrySource.USUARIO)
    assert view.draft.version == 1


def test_a_second_edit_uses_the_version_the_user_saw_and_raises_it(official_chosen):
    world = official_chosen
    first = add_activity(world, title="Primeira")
    second = add_activity(world, title="Segunda")
    save_entry(world, first)

    saved = save_entry(world, second, "Outro texto", version=1)

    assert saved.version == 2
    assert entry_of(stored_draft(world), first).text == TEXT
    assert entry_of(stored_draft(world), second).text == "Outro texto"


@pytest.mark.parametrize("sent", [0, 2])
def test_an_outdated_version_is_a_409_with_its_code_and_the_stored_text_stays(
    official_chosen, sent
):
    world = official_chosen
    activity = add_activity(world, title="Orientação")
    saved = save_entry(world, activity)

    with pytest.raises(StaleVersion) as error:
        save_entry(world, activity, "Texto de quem viu a versão antiga", version=sent)

    assert error.value.code == GenerationCode.VERSAO_DESATUALIZADA
    assert stored_draft(world) == saved


def test_a_first_save_with_a_version_other_than_0_is_stale_and_stores_nothing(official_chosen):
    world = official_chosen
    activity = add_activity(world)

    with pytest.raises(StaleVersion) as error:
        save_entry(world, activity, version=4)

    assert error.value.code == GenerationCode.VERSAO_DESATUALIZADA
    assert stored_draft(world) is None


def test_more_than_20000_characters_is_a_422_and_exactly_20000_is_saved(official_chosen):
    world = official_chosen
    activity = add_activity(world)

    with pytest.raises(ValidationFailed) as error:
        save_entry(world, activity, "a" * 20001)

    assert error.value.field == "text"
    assert stored_draft(world) is None
    assert entry_of(save_entry(world, activity, "a" * 20000), activity).text == "a" * 20000


def test_an_activity_validated_after_the_last_save_can_be_edited_too(official_chosen):
    world = official_chosen
    old = add_activity(world, title="Antiga")
    save_proposal(world)
    new = add_activity(world, title="Nova")

    saved = save_entry(world, new, version=1)

    assert saved.version == 2
    stored = stored_draft(world)
    assert [e.activity_id for e in section_of(stored, "1.3").entries] == [old.id, new.id]
    assert entry_of(stored, new).source is EntrySource.USUARIO
    view = get_draft_uc(world).execute(world.docente, world.process.id)
    assert view.alerts == ()


@pytest.mark.parametrize("status", [ProcessStatus.CONCLUIDO, ProcessStatus.ARQUIVADO])
def test_a_concluded_or_archived_process_refuses_the_save_and_stores_nothing(
    official_chosen, status
):
    world = official_chosen
    activity = add_activity(world)
    set_status(world, status)

    with pytest.raises(Conflict) as error:
        save_entry(world, activity)
    with pytest.raises(Conflict) as section_error:
        save_section_uc(world).execute(world.docente, world.process.id, "1.3", "livre", 0)

    assert error.value.code == GenerationCode.PROCESSO_SOMENTE_LEITURA
    assert section_error.value.code == GenerationCode.PROCESSO_SOMENTE_LEITURA
    assert stored_draft(world) is None


def test_a_process_out_of_reach_or_an_unknown_activity_or_section_is_not_found(official_chosen):
    world = official_chosen
    activity = add_activity(world)

    with pytest.raises(NotFound):
        save_entry(world, activity, actor=world.other_docente)
    with pytest.raises(NotFound):
        save_entry_uc(world).execute(world.docente, world.process.id, uuid.uuid4(), TEXT, 0)
    with pytest.raises(NotFound):
        save_section_uc(world).execute(world.docente, world.process.id, "9.9", "x", 0)
    assert stored_draft(world) is None


def test_the_free_text_of_a_section_is_saved_with_the_version_and_stays_with_the_entries(
    official_chosen,
):
    world = official_chosen
    activity = add_activity(world)

    created = save_section_uc(world).execute(world.docente, world.process.id, "2", "Texto livre", 0)
    again = save_section_uc(world).execute(
        world.docente, world.process.id, "2", "Texto livre revisto", 1
    )

    assert (created.version, again.version) == (1, 2)
    stored = stored_draft(world)
    assert section_of(stored, "2").free_text == "Texto livre revisto"
    assert entry_of(stored, activity).source is EntrySource.MODELO
    view = get_draft_uc(world).execute(world.docente, world.process.id)
    assert "2" not in view.empty_sections


def test_the_free_text_has_the_same_limit_and_the_same_version_rule(official_chosen):
    world = official_chosen
    add_activity(world)
    save_section_uc(world).execute(world.docente, world.process.id, "2", "livre", 0)

    with pytest.raises(ValidationFailed):
        save_section_uc(world).execute(world.docente, world.process.id, "2", "a" * 20001, 1)
    with pytest.raises(StaleVersion) as error:
        save_section_uc(world).execute(world.docente, world.process.id, "2", "outro", 0)

    assert error.value.code == GenerationCode.VERSAO_DESATUALIZADA
    assert section_of(stored_draft(world), "2").free_text == "livre"


def test_the_audit_of_a_save_has_the_version_and_the_operation_but_never_the_text(
    official_chosen,
):
    world = official_chosen
    activity = add_activity(world)
    save_entry(world, activity)

    with world.uow_factory() as uow:
        events = uow.audit.list_for("report_draft", str(world.process.id))

    [event] = events
    assert event.action is AuditAction.CREATE
    assert event.user_id == world.docente.id
    assert event.changes["version"] == {"before": 0, "after": 1}
    assert TEXT not in str(event.changes)
