"""GP-DEL-03 to GP-DEL-07, GP-DEL-09, GP-DEL-10 and the preview (GP-D7): deleting a process."""

import dataclasses
import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import text

from app.application.use_cases.processes import (
    ChangeProcessStatus,
    DeleteProcess,
    GetProcess,
    GetProcessDeletePreview,
)
from app.domain.entities.audit import AuditAction
from app.domain.entities.generated import DocumentFormat, DocumentKind, GeneratedFile
from app.domain.entities.process import ProcessStatus
from app.domain.errors import Conflict, Forbidden, NotFound
from app.domain.repositories.ports import JobStatus, ProcessDeletionCounts
from app.infrastructure.database.repositories import SqlUnitOfWork
from app.infrastructure.database.session import make_session_factory
from tests.integration.doc_usecases.generation_support import (
    add_activity,
    link,
    store_original,
)
from tests.integration.doc_usecases.support import pdf
from tests.integration.documents.generated_support import make_generation, make_wording_job
from tests.integration.documents.test_repositories import make_job

NOW = datetime(2026, 11, 18, 10, 0, tzinfo=UTC)


@pytest.fixture
def case(gen):
    """The main process with two input files, one activity linked to a document and one
    generated version with a PDF and a DOCX, every file really on the disk."""
    world = gen.world
    process = world.process
    docs = [store_original(gen, process, pdf(f"gp-{n}")) for n in range(2)]
    activity = add_activity(world, process)
    link(world, activity, docs[0])

    temp_pdf, temp_docx = (gen.generated.new_temp_path(process.id) for _ in range(2))
    temp_pdf.write_bytes(b"%PDF generated")
    temp_docx.write_bytes(b"docx generated")
    files = [
        GeneratedFile(
            DocumentFormat.PDF, gen.generated.commit(process.id, temp_pdf, "pdf"), "a" * 64, 14
        ),
        GeneratedFile(
            DocumentFormat.DOCX, gen.generated.commit(process.id, temp_docx, "docx"), "b" * 64, 14
        ),
    ]
    generation = make_generation(process, world.admin.id, DocumentKind.TABELA)
    with world.uow_factory() as uow:
        uow.generations.add(generation)
        uow.commit()
    with world.uow_factory() as uow:
        uow.generations.finish_ready(generation.id, NOW, files, {"total": "1"}, (), None)
        uow.commit()

    return SimpleNamespace(gen=gen, world=world, docs=docs, files=files)


def make_use_cases(case):
    world = case.world
    return (
        DeleteProcess(
            world.uow_factory, world.audit, world.policy, case.gen.originals, case.gen.generated
        ),
        GetProcessDeletePreview(world.uow_factory, world.audit, world.policy),
    )


def delete(case):
    return make_use_cases(case)[0]


def disk_files(case):
    return sorted(p for p in Path(case.gen.docs.storage_root).rglob("*") if p.is_file())


def count(world, table):
    with world.uow_factory() as uow:
        return uow._session.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()


def process_exists(world, process_id):
    with world.uow_factory() as uow:
        return uow.processes.get(process_id) is not None


def set_status(world, process, status):
    with world.uow_factory() as uow:
        current = uow.processes.get(process.id)
        uow.processes.update(dataclasses.replace(current, status=status), current.version)
        uow.commit()


def test_an_admin_deletes_the_process_and_everything_below_it(case):
    world = case.world

    delete(case).execute(world.admin, world.process.id)

    assert not process_exists(world, world.process.id)
    for table in (
        "documents",
        "activities",
        "activity_evidences",
        "generated_documents",
        "generated_files",
    ):
        assert count(world, table) == 0, table


def test_a_process_with_a_merged_activity_is_deleted_whole(case):
    """DUP-02: the merge keys (NO ACTION) do not block the single DELETE of the activities."""
    world = case.world
    with world.uow_factory() as uow:
        kept = uow.activities.list_for_process(world.process.id)[0]
    merged = add_activity(world, world.process, title="Duplicada")
    evidence = link(world, merged, case.docs[1])
    with world.uow_factory() as uow:
        uow.evidences.move([evidence.id], kept.id, merged.id)
        current = uow.activities.get(merged.id)
        uow.activities.set_merged_into(current, kept.id, current.version)
        uow.commit()
    assert count(world, "activities") == 2

    delete(case).execute(world.admin, world.process.id)

    assert not process_exists(world, world.process.id)
    for table in ("activities", "activity_evidences", "documents"):
        assert count(world, table) == 0, table


def test_the_main_process_goes_and_the_other_process_stays(case):
    world = case.world
    other_doc = store_original(case.gen, world.ifch_process, pdf("other"))

    delete(case).execute(world.admin, world.process.id)

    assert process_exists(world, world.ifch_process.id)
    with world.uow_factory() as uow:
        assert uow.documents.get(other_doc.id) is not None
    assert [p.name for p in disk_files(case)] == [other_doc.internal_name]


def test_the_files_of_inputs_and_generated_documents_leave_the_disk(case):
    assert len(disk_files(case)) == 4

    delete(case).execute(case.world.admin, case.world.process.id)

    assert disk_files(case) == []


def process_dirs(case, process_id):
    root = Path(case.gen.docs.storage_root)
    return [d for d in (root / "uploads" / str(process_id), root / "generated" / str(process_id))]


def test_the_empty_storage_directories_of_the_process_are_removed(case):
    process_id = case.world.process.id
    assert all(d.is_dir() for d in process_dirs(case, process_id))

    delete(case).execute(case.world.admin, process_id)

    assert not any(d.exists() for d in process_dirs(case, process_id))
    root = Path(case.gen.docs.storage_root)
    assert (root / "uploads").is_dir() and (root / "generated").is_dir()


def test_the_directory_of_the_other_process_stays(case):
    world = case.world
    other_doc = store_original(case.gen, world.ifch_process, pdf("other"))

    delete(case).execute(world.admin, world.process.id)

    root = Path(case.gen.docs.storage_root)
    assert (root / "uploads" / str(world.ifch_process.id) / other_doc.internal_name).is_file()


def test_a_directory_holding_a_foreign_file_is_kept_with_that_file(case):
    world = case.world
    uploads_dir, generated_dir = process_dirs(case, world.process.id)
    stray = uploads_dir / "nao-e-nosso.txt"
    stray.write_text("alheio")

    delete(case).execute(world.admin, world.process.id)

    assert not process_exists(world, world.process.id)
    assert stray.read_text() == "alheio"
    assert uploads_dir.is_dir()
    assert not generated_dir.exists()


def test_a_directory_that_cannot_be_removed_only_logs_and_the_deletion_stands(case, caplog):
    world = case.world

    class Stuck:
        def __init__(self, inner):
            self._inner = inner

        def delete(self, process_id, internal_name):
            self._inner.delete(process_id, internal_name)

        def remove_process_dir(self, process_id):
            raise PermissionError(f"{case.gen.docs.storage_root}/uploads/{process_id}")

    use_case = DeleteProcess(
        world.uow_factory, world.audit, world.policy, Stuck(case.gen.originals), case.gen.generated
    )

    with caplog.at_level(logging.WARNING):
        use_case.execute(world.admin, world.process.id)

    assert not process_exists(world, world.process.id)
    uploads_dir, generated_dir = process_dirs(case, world.process.id)
    assert uploads_dir.is_dir() and not generated_dir.exists()
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    assert str(world.process.id) in warnings[0].getMessage()
    assert str(case.gen.docs.storage_root) not in caplog.text


def test_the_owner_docente_can_delete(case):
    world = case.world
    delete(case).execute(world.docente, world.process.id)

    assert not process_exists(world, world.process.id)


def test_the_creator_can_delete_even_when_not_admin(case):
    world = case.world
    with world.uow_factory() as uow:
        current = uow.processes.get(world.process.id)
        uow.processes.update(
            dataclasses.replace(current, created_by=world.secretaria.id), current.version
        )
        uow.commit()

    delete(case).execute(world.secretaria, world.process.id)

    assert not process_exists(world, world.process.id)


def test_a_reader_who_is_not_the_owner_gets_403_and_nothing_is_deleted(case):
    world = case.world

    with pytest.raises(Forbidden, match="Apenas ADMIN ou o dono"):
        delete(case).execute(world.secretaria, world.process.id)

    assert process_exists(world, world.process.id)
    assert len(disk_files(case)) == 4
    assert count(world, "documents") == 2


def test_an_actor_who_cannot_read_the_process_gets_404(case):
    world = case.world
    for actor in (world.other_docente, world.other_secretaria):
        with pytest.raises(NotFound):
            delete(case).execute(actor, world.process.id)

    assert process_exists(world, world.process.id)


def test_an_unknown_process_is_404(case):
    with pytest.raises(NotFound):
        delete(case).execute(case.world.admin, uuid.uuid4())


@pytest.mark.parametrize("status", list(ProcessStatus))
def test_a_process_can_be_deleted_in_any_status(case, status):
    world = case.world
    set_status(world, world.process, status)

    delete(case).execute(world.admin, world.process.id)

    assert not process_exists(world, world.process.id)


def test_a_deleted_process_answers_404_to_a_read(case):
    world = case.world
    delete(case).execute(world.admin, world.process.id)

    with pytest.raises(NotFound):
        GetProcess(world.uow_factory, world.audit, world.policy).execute(
            world.admin, world.process.id
        )
    with pytest.raises(NotFound):
        delete(case).execute(world.admin, world.process.id)


def expect_busy(case):
    """The deletion answers 409 OPERACAO_EM_ANDAMENTO and changes nothing (GP-DEL-07)."""
    world = case.world
    audit_rows = count(world, "audit_logs")
    with pytest.raises(Conflict) as raised:
        delete(case).execute(world.admin, world.process.id)
    assert raised.value.code == "OPERACAO_EM_ANDAMENTO"
    assert process_exists(world, world.process.id)
    assert count(world, "documents") == 2
    assert count(world, "generated_files") == 2
    assert len(disk_files(case)) == 4
    assert count(world, "audit_logs") == audit_rows


@pytest.mark.parametrize("status", [JobStatus.PENDENTE, JobStatus.PROCESSANDO])
def test_a_document_being_processed_blocks_the_deletion(case, status):
    with case.world.uow_factory() as uow:
        uow.jobs.add(make_job(case.docs[0].id, status=status))
        uow.commit()

    expect_busy(case)


def test_a_generation_in_progress_blocks_the_deletion(case):
    world = case.world
    with world.uow_factory() as uow:
        uow.generations.add(make_generation(world.process, world.admin.id, DocumentKind.RELATORIO))
        uow.commit()

    expect_busy(case)


def test_a_wording_in_progress_blocks_the_deletion(case):
    world = case.world
    with world.uow_factory() as uow:
        uow.wording_jobs.add(make_wording_job(world.process, world.admin.id))
        uow.commit()

    expect_busy(case)


def test_the_deletion_writes_a_delete_event_with_the_previous_values(case):
    world = case.world
    before = world.process

    delete(case).execute(world.admin, world.process.id)

    with world.uow_factory() as uow:
        events = uow.audit.list_for("process", str(before.id))
    [event] = [e for e in events if e.action is AuditAction.DELETE]
    assert event.user_id == world.admin.id
    assert event.changes["current_class"] == {"before": before.current_class, "after": None}
    assert event.changes["status"] == {"before": before.status.value, "after": None}


def test_the_earlier_audit_events_of_the_process_survive_the_deletion(case):
    world = case.world
    ChangeProcessStatus(world.uow_factory, world.audit, world.policy).execute(
        world.admin, world.process.id, ProcessStatus.ARQUIVADO, world.process.version
    )
    with world.uow_factory() as uow:
        earlier = list(uow.audit.list_for("process", str(world.process.id)))
    assert AuditAction.STATUS in [e.action for e in earlier]

    delete(case).execute(world.admin, world.process.id)

    with world.uow_factory() as uow:
        events = list(uow.audit.list_for("process", str(world.process.id)))
    assert events[:-1] == earlier
    assert events[-1].action is AuditAction.DELETE


def test_a_file_that_cannot_be_removed_only_logs_and_the_deletion_stands(case, caplog):
    world = case.world
    failing = case.docs[0].internal_name

    class Flaky:
        def __init__(self, inner):
            self._inner = inner

        def delete(self, process_id, internal_name):
            if internal_name == failing:
                raise PermissionError(f"{self._inner.path(process_id, internal_name)}")
            self._inner.delete(process_id, internal_name)

        def remove_process_dir(self, process_id):
            self._inner.remove_process_dir(process_id)

    use_case = DeleteProcess(
        world.uow_factory, world.audit, world.policy, Flaky(case.gen.originals), case.gen.generated
    )

    with caplog.at_level(logging.WARNING):
        use_case.execute(world.admin, world.process.id)

    assert not process_exists(world, world.process.id)
    assert [p.name for p in disk_files(case)] == [failing]
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    assert str(case.docs[0].id) in warnings[0].getMessage()
    assert failing not in caplog.text
    assert str(case.gen.docs.storage_root) not in caplog.text
    assert "Docente" not in caplog.text


def test_when_the_transaction_fails_nothing_is_deleted_and_no_file_is_removed(case, engine):
    world = case.world
    sessions = make_session_factory(engine)
    audit_rows = count(world, "audit_logs")

    class FailingCommit(SqlUnitOfWork):
        def commit(self):
            raise RuntimeError("commit failed")

    with pytest.raises(RuntimeError, match="commit failed"):
        DeleteProcess(
            lambda: FailingCommit(sessions),
            world.audit,
            world.policy,
            case.gen.originals,
            case.gen.generated,
        ).execute(world.admin, world.process.id)

    assert process_exists(world, world.process.id)
    assert count(world, "documents") == 2
    assert count(world, "generated_files") == 2
    assert count(world, "audit_logs") == audit_rows
    assert len(disk_files(case)) == 4


def test_the_preview_counts_inputs_activities_and_generated_documents(case):
    world = case.world
    add_activity(world, world.process)
    store_original(case.gen, world.ifch_process, pdf("elsewhere"))

    counts = make_use_cases(case)[1].execute(world.docente, world.process.id)

    assert counts == ProcessDeletionCounts(documents=2, activities=2, generated_documents=1)


def test_the_preview_follows_the_same_permissions_as_the_deletion(case):
    world = case.world
    preview = make_use_cases(case)[1]

    with pytest.raises(Forbidden):
        preview.execute(world.secretaria, world.process.id)
    with pytest.raises(NotFound):
        preview.execute(world.other_docente, world.process.id)
    with pytest.raises(NotFound):
        preview.execute(world.admin, uuid.uuid4())
