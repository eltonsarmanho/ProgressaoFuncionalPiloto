"""REL-09, REL-10, REL-12: running the generation of the activities report."""

from dataclasses import replace

from app.application.services.generation_inputs import load_generation_inputs
from app.domain.entities.generated import (
    DocumentFormat,
    DocumentKind,
    GenerationAlertCode,
    GenerationState,
)
from app.domain.entities.report import DraftEntry, EntrySource
from app.domain.rules.report_draft import propose_draft
from app.infrastructure.documents.config_loader import load_report_config
from tests.integration.doc_usecases.generation_support import add_activity
from tests.integration.doc_usecases.test_run_generation_table import (
    docx_text,
    file_of,
    generate,
    pdf_text,
)

EDITED = "Texto escrito pelo usuário, que a geração não pode mudar."


def proposal(world):
    config = load_report_config()
    with world.uow_factory() as uow:
        inputs = load_generation_inputs(uow, uow.processes.get(world.process.id))
    return propose_draft(
        config.template, inputs.activities, config.group_map, process_id=world.process.id
    )


def save_with_edited_text(world, activity):
    """Saves the draft with the text of `activity` typed by the user; returns the saved draft."""
    draft = proposal(world)
    sections = tuple(
        replace(
            s,
            entries=tuple(
                DraftEntry(e.activity_id, EDITED, EntrySource.USUARIO)
                if e.activity_id == activity.id
                else e
                for e in s.entries
            ),
        )
        for s in draft.sections
    )
    with world.uow_factory() as uow:
        saved = uow.report_drafts.create(replace(draft, sections=sections), world.admin.id, 0)
        uow.commit()
    return saved


def stored_draft(world):
    with world.uow_factory() as uow:
        return uow.report_drafts.get(world.process.id)


def test_the_document_uses_the_text_the_user_edited_and_leaves_the_draft_as_it_was(gen):
    world = gen.world
    edited = add_activity(world, title="Orientação editada")
    add_activity(world, title="Orientação do modelo", item_number=8)
    saved = save_with_edited_text(world, edited)

    done = generate(gen, DocumentKind.RELATORIO)

    assert done.state is GenerationState.PRONTO
    for fmt, text in (
        (DocumentFormat.DOCX, docx_text),
        (DocumentFormat.PDF, pdf_text),
    ):
        content = text(file_of(gen, done, fmt)[1])
        assert " ".join(EDITED.split()[:4]) in " ".join(content.split())
        assert "Orientação do modelo" in content
    assert stored_draft(world) == saved


def test_the_snapshot_keeps_sections_activities_and_the_source_of_each_text(gen):
    world = gen.world
    edited = add_activity(world, title="Orientação editada")
    other = add_activity(world, title="Orientação do modelo", item_number=8)
    save_with_edited_text(world, edited)

    done = generate(gen, DocumentKind.RELATORIO)

    entries = {
        e["activity_id"]: e
        for section in done.snapshot["report"]["sections"]
        for e in section["entries"]
    }
    assert entries[str(edited.id)]["source"] == "USUARIO"
    assert entries[str(edited.id)]["text"] == EDITED
    assert entries[str(other.id)]["source"] == "MODELO"
    assert "Orientação do modelo" in entries[str(other.id)]["text"]
    assert done.snapshot["template"] == {
        "id": load_report_config().template.id,
        "version": load_report_config().template.version,
    }
    assert [s["key"] for s in done.snapshot["report"]["sections"]] == ["1.3"]


def test_without_a_saved_draft_it_generates_from_the_proposal_and_saves_nothing(gen):
    world = gen.world
    add_activity(world, title="Orientação sem rascunho")

    done = generate(gen, DocumentKind.RELATORIO)

    assert done.state is GenerationState.PRONTO
    assert "Orientação sem rascunho" in pdf_text(file_of(gen, done, DocumentFormat.PDF)[1])
    entry = done.snapshot["report"]["sections"][0]["entries"][0]
    assert entry["source"] == "MODELO"
    assert stored_draft(world) is None


def test_an_activity_validated_after_the_draft_was_saved_goes_in_with_a_stale_alert(gen):
    world = gen.world
    first = add_activity(world, title="Primeira orientação")
    save_with_edited_text(world, first)
    add_activity(world, title="Orientação nova", item_number=8)

    done = generate(gen, DocumentKind.RELATORIO)

    assert "Orientação nova" in pdf_text(file_of(gen, done, DocumentFormat.PDF)[1])
    assert [a.code for a in done.alerts] == [GenerationAlertCode.RASCUNHO_DESATUALIZADO]
