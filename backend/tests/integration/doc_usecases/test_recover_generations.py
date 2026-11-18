"""VER-08, REL-14: what a restart leaves behind is closed as interrupted, never repeated."""

from datetime import timedelta

from app.application.use_cases.generated_documents import RecoverInterruptedGenerations
from app.domain.entities.audit import AuditAction
from app.domain.entities.generated import (
    DocumentFormat,
    DocumentKind,
    GeneratedFile,
    GenerationCode,
    GenerationState,
)
from tests.integration.doc_usecases.generation_support import MOMENT
from tests.integration.documents.generated_support import (
    make_draft,
    make_generation,
    make_wording_job,
)


def recover(gen) -> RecoverInterruptedGenerations:
    world = gen.world
    return RecoverInterruptedGenerations(world.uow_factory, world.audit, gen.clock, gen.generated)


def add_generation(gen, kind, started: bool, later: int = 0):
    world = gen.world
    row = make_generation(
        world.process, world.admin.id, kind, requested_at=MOMENT + timedelta(minutes=later)
    )
    with world.uow_factory() as uow:
        uow.generations.add(row)
        if started:
            assert uow.generations.claim_next(MOMENT).id == row.id
        uow.commit()
    return row


def add_wording(gen, section_key, started: bool, later: int = 0):
    world = gen.world
    job = make_wording_job(
        world.process, world.admin.id, section_key, requested_at=MOMENT + timedelta(minutes=later)
    )
    with world.uow_factory() as uow:
        uow.wording_jobs.add(job)
        if started:
            assert uow.wording_jobs.claim_next(MOMENT).id == job.id
        uow.commit()
    return job


def state_of(gen, row):
    with gen.world.uow_factory() as uow:
        return uow.generations.get(row.id)


def test_started_generations_and_wordings_are_interrupted_and_the_waiting_ones_stay_queued(gen):
    running = add_generation(gen, DocumentKind.TABELA, started=True)
    waiting = add_generation(gen, DocumentKind.RELATORIO, started=False, later=1)
    word_running = add_wording(gen, "1.1", started=True)
    word_waiting = add_wording(gen, "1.2", started=False, later=1)

    changed = recover(gen).execute()

    assert changed == 2
    interrupted = state_of(gen, running)
    assert (interrupted.state, interrupted.error_code) == (
        GenerationState.FALHOU,
        GenerationCode.INTERROMPIDA,
    )
    assert state_of(gen, waiting).state is GenerationState.GERANDO
    with gen.world.uow_factory() as uow:
        job = uow.wording_jobs.get(word_running.id)
        assert (job.state, job.error_code) == (GenerationState.FALHOU, GenerationCode.INTERROMPIDA)
        assert uow.wording_jobs.get(word_waiting.id).state is GenerationState.GERANDO
        # nothing was requeued: the only rows an executor can claim are the waiting ones
        assert uow.generations.claim_next(MOMENT).id == waiting.id
        assert uow.generations.claim_next(MOMENT) is None
        assert uow.wording_jobs.claim_next(MOMENT).id == word_waiting.id
        assert uow.wording_jobs.claim_next(MOMENT) is None


def test_each_interruption_is_audited_with_the_code(gen):
    running = add_generation(gen, DocumentKind.TABELA, started=True)
    job = add_wording(gen, "1.1", started=True)

    recover(gen).execute()

    with gen.world.uow_factory() as uow:
        for entity, entity_id in (
            ("generated_document", running.id),
            ("report_wording_job", job.id),
        ):
            [event] = uow.audit.list_for(entity, str(entity_id))
            assert event.action is AuditAction.STATUS
            assert event.changes["state"] == {"before": "GERANDO", "after": "FALHOU"}
            assert event.changes["error_code"] == {"before": None, "after": "INTERROMPIDA"}


def stored(gen):
    root = gen.docs.storage_root / "generated"
    return sorted(p.name for p in root.rglob("*") if p.is_file())


def test_temporary_files_and_files_without_a_row_go_and_the_files_of_a_row_stay(gen):
    world = gen.world
    row = add_generation(gen, DocumentKind.TABELA, started=False)
    kept_temp = gen.generated.new_temp_path(world.process.id)
    kept = gen.generated.commit(
        world.process.id, gen.generated.new_temp_path(world.process.id), "pdf"
    )
    orphan = gen.generated.commit(
        world.process.id, gen.generated.new_temp_path(world.process.id), "docx"
    )
    with world.uow_factory() as uow:
        uow.generations.claim_next(MOMENT)
        uow.generations.finish_ready(
            row.id, MOMENT, [GeneratedFile(DocumentFormat.PDF, kept, "a" * 64, 10)], {}, ()
        )
        uow.commit()
    assert kept_temp.exists()

    recover(gen).execute()

    assert stored(gen) == [kept]
    assert orphan not in stored(gen)


def test_the_text_of_the_draft_is_not_changed_by_the_recovery(gen):
    world = gen.world
    with world.uow_factory() as uow:
        saved = uow.report_drafts.create(make_draft(world.process), world.admin.id, 0)
        uow.commit()
    add_wording(gen, "1.1", started=True)

    recover(gen).execute()

    with world.uow_factory() as uow:
        assert uow.report_drafts.get(world.process.id) == saved


def test_running_the_recovery_again_changes_nothing(gen):
    add_generation(gen, DocumentKind.TABELA, started=True)
    add_wording(gen, "1.1", started=True)
    assert recover(gen).execute() == 2

    assert recover(gen).execute() == 0

    with gen.world.uow_factory() as uow:
        [row] = uow.generations.list_for_process(gen.world.process.id)
        assert len(uow.audit.list_for("generated_document", str(row.id))) == 1
