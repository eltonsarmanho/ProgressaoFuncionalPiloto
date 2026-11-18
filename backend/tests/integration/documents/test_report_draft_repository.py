"""REL-03, REL-07, REL-08: the report draft repository on real PostgreSQL."""

import dataclasses
import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.domain.entities.generated import GenerationAlert, GenerationAlertCode
from app.domain.entities.report import DraftEntry, DraftSection, EntrySource
from app.domain.errors import Conflict, NotFound, StaleVersion
from app.infrastructure.database.repositories import SqlReportDraftRepository
from tests.integration.documents.generated_support import make_draft


def repo_call(session_factory, call):
    """Runs `call(repository)` in its own session and commits."""
    with session_factory() as session:
        result = call(SqlReportDraftRepository(session))
        session.commit()
    return result


def saved(session_factory, process, base, draft=None):
    draft = draft or make_draft(process)
    repo_call(session_factory, lambda r: r.create(draft, base["admin"].id, 0))
    return draft


def get(session_factory, process_id):
    with session_factory() as session:
        return SqlReportDraftRepository(session).get(process_id)


def test_a_process_without_a_saved_draft_has_none(session_factory, process):
    assert get(session_factory, process.id) is None


def test_the_first_save_expects_version_0_and_stores_version_1_with_everything(
    session_factory, process, base
):
    warned = DraftEntry(
        uuid.uuid4(),
        "Texto",
        EntrySource.MODELO,
        (GenerationAlert(GenerationAlertCode.REDACAO_REJEITADA, "NUMERO"),),
    )
    draft = make_draft(
        process,
        (
            DraftSection(
                "1.1",
                "Ensino",
                free_text="livre",
                entries=(warned, DraftEntry(uuid.uuid4(), "Ed", EntrySource.USUARIO)),
                warnings=(GenerationAlert(GenerationAlertCode.REDACAO_INDISPONIVEL),),
            ),
        ),
    )

    created = repo_call(session_factory, lambda r: r.create(draft, base["admin"].id, 0))

    expected = dataclasses.replace(draft, version=1)
    assert created == expected
    assert get(session_factory, process.id) == expected


def test_a_first_save_with_a_version_other_than_0_is_stale_and_stores_nothing(
    session_factory, process, base
):
    with pytest.raises(StaleVersion):
        repo_call(session_factory, lambda r: r.create(make_draft(process), base["admin"].id, 3))

    assert get(session_factory, process.id) is None


def test_a_second_create_for_the_same_process_conflicts(session_factory, process, base):
    saved(session_factory, process, base)

    with pytest.raises(Conflict):
        repo_call(session_factory, lambda r: r.create(make_draft(process), base["admin"].id, 0))


def test_update_entry_replaces_the_text_and_source_and_raises_the_version(
    session_factory, process, base
):
    draft = saved(session_factory, process, base)
    target = draft.sections[0].entries[1]
    edited = DraftEntry(target.activity_id, "Texto do docente", EntrySource.USUARIO)

    result = repo_call(
        session_factory, lambda r: r.update_entry(process.id, 1, edited, base["admin"].id)
    )

    assert result.version == 2
    entries = get(session_factory, process.id).sections[0].entries
    assert entries[0] == draft.sections[0].entries[0]
    assert entries[1] == edited
    assert get(session_factory, process.id).sections[1] == draft.sections[1]


def test_update_entry_with_a_stale_version_raises_and_keeps_the_stored_text(
    session_factory, process, base
):
    draft = saved(session_factory, process, base)
    target = draft.sections[0].entries[0]
    edited = DraftEntry(target.activity_id, "novo", EntrySource.USUARIO)

    with pytest.raises(StaleVersion):
        repo_call(
            session_factory, lambda r: r.update_entry(process.id, 7, edited, base["admin"].id)
        )

    stored = get(session_factory, process.id)
    assert stored.version == 1
    assert stored.sections[0].entries[0].text == "Aula A"


def test_update_of_an_unknown_draft_or_activity_is_not_found(session_factory, process, base):
    ghost = DraftEntry(uuid.uuid4(), "x", EntrySource.USUARIO)
    with pytest.raises(NotFound):
        repo_call(session_factory, lambda r: r.update_entry(process.id, 1, ghost, base["admin"].id))

    saved(session_factory, process, base)
    with pytest.raises(NotFound):
        repo_call(session_factory, lambda r: r.update_entry(process.id, 1, ghost, base["admin"].id))


def test_update_section_replaces_the_free_text_and_raises_the_version(
    session_factory, process, base
):
    draft = saved(session_factory, process, base)

    result = repo_call(
        session_factory,
        lambda r: r.update_section(process.id, 1, "1.2", "Outro texto", base["admin"].id),
    )

    assert result.version == 2
    stored = get(session_factory, process.id)
    assert stored.sections[1].free_text == "Outro texto"
    assert stored.sections[1].entries == draft.sections[1].entries
    assert stored.sections[0] == draft.sections[0]


def test_update_section_with_a_stale_version_or_unknown_section_fails_without_writing(
    session_factory, process, base
):
    saved(session_factory, process, base)

    with pytest.raises(StaleVersion):
        repo_call(
            session_factory,
            lambda r: r.update_section(process.id, 0, "1.1", "x", base["admin"].id),
        )
    with pytest.raises(NotFound):
        repo_call(
            session_factory,
            lambda r: r.update_section(process.id, 1, "9.9", "x", base["admin"].id),
        )

    stored = get(session_factory, process.id)
    assert (stored.version, stored.sections[0].free_text) == (1, "")


def test_move_entry_puts_it_at_the_end_of_the_target_section(session_factory, process, base):
    draft = saved(session_factory, process, base)
    moved = draft.sections[0].entries[0]
    relocated = DraftEntry(moved.activity_id, "Texto novo da seção", EntrySource.MODELO)

    result = repo_call(
        session_factory,
        lambda r: r.move_entry(process.id, 1, "1.2", relocated, base["admin"].id),
    )

    assert result.version == 2
    stored = get(session_factory, process.id)
    assert [e.text for e in stored.sections[0].entries] == ["Aula B"]
    assert [e.text for e in stored.sections[1].entries] == ["Projeto", "Texto novo da seção"]


def test_move_entry_with_a_stale_version_or_unknown_target_fails_without_writing(
    session_factory, process, base
):
    draft = saved(session_factory, process, base)
    entry = draft.sections[0].entries[0]

    with pytest.raises(StaleVersion):
        repo_call(
            session_factory,
            lambda r: r.move_entry(process.id, 5, "1.2", entry, base["admin"].id),
        )
    with pytest.raises(NotFound):
        repo_call(
            session_factory,
            lambda r: r.move_entry(process.id, 1, "9.9", entry, base["admin"].id),
        )

    assert get(session_factory, process.id) == dataclasses.replace(draft, version=1)


def test_apply_wording_replaces_only_entries_that_are_still_not_from_the_user(
    session_factory, process, base
):
    draft = saved(session_factory, process, base)
    first, second = draft.sections[0].entries
    # The user edited the second entry while the wording ran.
    typed = DraftEntry(second.activity_id, "Texto do docente", EntrySource.USUARIO)
    repo_call(session_factory, lambda r: r.update_entry(process.id, 1, typed, base["admin"].id))
    warning = GenerationAlert(GenerationAlertCode.REDACAO_REJEITADA, "NUMERO")
    worded = DraftSection(
        "1.1",
        "Ensino",
        entries=(
            DraftEntry(first.activity_id, "Redação da IA", EntrySource.IA),
            DraftEntry(second.activity_id, "Redação da IA 2", EntrySource.IA),
        ),
        warnings=(warning,),
    )

    result = repo_call(session_factory, lambda r: r.apply_wording_locked(process.id, worded))

    stored = get(session_factory, process.id)
    assert result == stored
    assert stored.sections[0].entries[0] == DraftEntry(
        first.activity_id, "Redação da IA", EntrySource.IA
    )
    assert stored.sections[0].entries[1] == typed
    assert stored.sections[0].warnings == (warning,)
    assert stored.sections[1] == draft.sections[1]


def test_apply_wording_does_not_change_the_version_and_an_edit_with_it_still_succeeds(
    session_factory, process, base
):
    draft = saved(session_factory, process, base)
    worded = dataclasses.replace(
        draft.sections[1],
        entries=(DraftEntry(draft.sections[1].entries[0].activity_id, "IA", EntrySource.IA),),
    )
    result = repo_call(session_factory, lambda r: r.apply_wording_locked(process.id, worded))
    assert result.version == 1

    other = draft.sections[0].entries[0]
    edited = DraftEntry(other.activity_id, "Edição em voo", EntrySource.USUARIO)
    after = repo_call(
        session_factory, lambda r: r.update_entry(process.id, 1, edited, base["admin"].id)
    )

    assert after.version == 2
    stored = get(session_factory, process.id)
    assert stored.sections[0].entries[0] == edited
    assert stored.sections[1].entries[0].text == "IA"


def test_apply_wording_locks_the_row_until_the_transaction_ends(session_factory, process, base):
    draft = saved(session_factory, process, base)
    worded = dataclasses.replace(draft.sections[1])

    with session_factory() as holder, session_factory() as other:
        SqlReportDraftRepository(holder).apply_wording_locked(process.id, worded)
        with pytest.raises(OperationalError):
            other.execute(
                text("SELECT id FROM report_drafts WHERE process_id = :p FOR UPDATE NOWAIT"),
                {"p": process.id},
            )


def test_apply_wording_of_an_unknown_draft_or_section_is_not_found(session_factory, process, base):
    section = DraftSection("1.1", "Ensino")
    with pytest.raises(NotFound):
        repo_call(session_factory, lambda r: r.apply_wording_locked(process.id, section))

    saved(session_factory, process, base)
    with pytest.raises(NotFound):
        repo_call(
            session_factory,
            lambda r: r.apply_wording_locked(process.id, DraftSection("9.9", "x")),
        )
