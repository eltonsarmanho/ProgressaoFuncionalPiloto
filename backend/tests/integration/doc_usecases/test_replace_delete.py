"""DOC-09, DOC-10, DOC-12, DOC-13: ReplaceDocument and DeleteDocument."""

import dataclasses
import uuid

import pytest

from app.application.use_cases.documents import DuplicateDocument, UploadRejected
from app.application.use_cases.scoring import ActivityData
from app.domain.entities.activity import ActivityStatus
from app.domain.entities.audit import AuditAction
from app.domain.entities.document import DocumentStatus, RunStatus
from app.domain.entities.process import ProcessStatus
from app.domain.errors import Conflict, NotFound, ValidationFailed
from app.domain.repositories.ports import JobStatus
from tests.integration.doc_usecases.support import (
    draft_activity,
    finish_processing,
    link,
    pdf,
)
from tests.support import synthetic_docs as synth

AUTO_JUSTIFICATION = "Substituída por reprocessamento do documento"


def processed(docs, label, process=None, name="original.pdf", **options):
    """A document the executor already finished, with an active run; returns (document, run)."""
    w = docs.world
    document = docs.upload_one(w.docente, process or w.process, pdf(label), name)
    return finish_processing(w, document, **options)


def reload(docs, document_id):
    with docs.world.uow_factory() as uow:
        return uow.documents.get(document_id)


def events(docs, entity, entity_id):
    with docs.world.uow_factory() as uow:
        return list(uow.audit.list_for(entity, str(entity_id)))


def runs(docs, document_id):
    with docs.world.uow_factory() as uow:
        return list(uow.extractions.list_runs(document_id))


# --- ReplaceDocument -----------------------------------------------------------------------


def test_replace_keeps_the_id_stores_the_new_file_and_removes_the_old_one(docs, stored_files):
    w = docs.world
    document, _ = processed(docs, "antigo")
    old_path = docs.storage.path(w.process.id, document.internal_name)
    new_content = pdf("novo", pages=2)

    replaced = docs.replace.execute(w.docente, document.id, docs.incoming(new_content, "novo.pdf"))

    current = reload(docs, document.id)
    assert replaced.id == document.id == current.id
    assert current.original_name == "novo.pdf"
    assert current.sha256 != document.sha256
    assert current.size_bytes == len(new_content)
    assert current.page_count == 2
    assert current.status is DocumentStatus.PENDENTE
    assert current.internal_name != document.internal_name
    assert not old_path.exists()
    [stored] = stored_files()
    assert stored == docs.storage.path(w.process.id, current.internal_name)
    assert stored.read_bytes() == new_content


def test_replace_restarts_processing_with_a_new_pending_job(docs):
    w = docs.world
    document, _ = processed(docs, "reinicia")

    docs.replace.execute(w.docente, document.id, docs.incoming(pdf("reinicia-novo")))

    with w.uow_factory() as uow:
        job = uow.jobs.active_for_document(document.id)
    assert job is not None and job.status is JobStatus.PENDENTE


def test_replace_marks_the_active_run_replaced(docs):
    w = docs.world
    document, run = processed(docs, "run")

    docs.replace.execute(w.docente, document.id, docs.incoming(pdf("run-novo")))

    assert [(r.id, r.status) for r in runs(docs, document.id)] == [(run.id, RunStatus.SUBSTITUIDA)]


def test_replace_clears_the_suggestions_of_the_old_file_but_keeps_the_manual_ones(docs):
    w = docs.world
    document, _ = processed(docs, "sugestoes")
    with w.uow_factory() as uow:
        current = uow.documents.get(document.id)
        uow.documents.update(
            dataclasses.replace(
                current,
                suggested_type="DECLARACAO_BANCA",
                suggested_category="BANCA_TCC_GRADUACAO",
                manual_type="CERTIFICADO",
                manual_category="CURSO_CONCLUIDO",
                status_code="TRUNCADO",
            ),
            current.version,
        )
        uow.commit()

    docs.replace.execute(w.docente, document.id, docs.incoming(pdf("sugestoes-novo")))

    current = reload(docs, document.id)
    assert (current.suggested_type, current.suggested_category, current.status_code) == (
        None,
        None,
        None,
    )
    assert (current.manual_type, current.manual_category) == ("CERTIFICADO", "CURSO_CONCLUIDO")


def test_replace_audits_old_and_new_name_and_hash_without_content(docs):
    w = docs.world
    document, _ = processed(docs, "auditado", name="antes.pdf")
    docs.clock.advance(hours=1)
    new_content = synth.pdf_with_text(["Conteudo secreto novo"])
    new_file = docs.incoming(new_content, "depois.pdf")

    docs.replace.execute(w.docente, document.id, new_file)

    *_, event = events(docs, "document", document.id)
    assert event.user_id == w.docente.id
    assert event.occurred_at == docs.clock.now()
    assert event.action is AuditAction.UPDATE
    assert event.changes["operation"]["after"] == "REPLACE"
    assert event.changes["original_name"] == {"before": "antes.pdf", "after": "depois.pdf"}
    assert event.changes["sha256"] == {"before": document.sha256, "after": new_file.sha256}
    assert event.changes["status"] == {"before": "PROCESSADO", "after": "PENDENTE"}
    assert "secreto" not in str(event.changes)


def test_replace_rejects_only_the_untouched_drafts_of_the_old_run(docs):
    w = docs.world
    document, run = processed(docs, "rascunhos")
    other_document, other_run = processed(docs, "outro-doc", name="outro.pdf")
    untouched = draft_activity(w, w.process, "Intocada", run=run)
    edited = draft_activity(w, w.process, "Editada", run=run)
    edited = w.update.execute(
        w.admin,
        edited.id,
        ActivityData(title="Editada pelo usuario", group_number=3, item_number=4),
        edited.version,
        None,
    )
    validated = draft_activity(w, w.process, "Validada", run=run)
    validated = w.change_status.execute(
        w.admin, validated.id, ActivityStatus.VALIDADA, validated.version, "Conferida"
    )
    of_other_run = draft_activity(w, w.process, "De outro documento", run=other_run)

    docs.replace.execute(w.docente, document.id, docs.incoming(pdf("rascunhos-novo")))

    with w.uow_factory() as uow:
        status = {a.title: a for a in uow.activities.list_for_process(w.process.id)}
        rejection = uow.audit.list_for("activity", str(untouched.id))[-1]
    assert status["Intocada"].status is ActivityStatus.REJEITADA
    assert status["Editada pelo usuario"].status is ActivityStatus.AGUARDANDO_REVISAO
    assert status["Validada"].status is ActivityStatus.VALIDADA
    assert status["De outro documento"].status is ActivityStatus.AGUARDANDO_REVISAO
    assert rejection.action is AuditAction.STATUS
    assert rejection.justification == AUTO_JUSTIFICATION
    assert rejection.user_id == w.docente.id
    assert (edited.version, validated.version, of_other_run.version) == (2, 2, 1)


def test_replace_with_an_invalid_file_gives_422_and_changes_nothing(docs, stored_files):
    w = docs.world
    document, run = processed(docs, "intacto")
    before_files = stored_files()

    with pytest.raises(UploadRejected) as error:
        docs.replace.execute(
            w.docente, document.id, docs.incoming(synth.pdf_with_javascript(), "js.pdf")
        )

    assert (error.value.field, error.value.code) == ("arquivo", "ARQUIVO_INVALIDO")
    assert reload(docs, document.id) == document
    assert stored_files() == before_files
    assert [r.status for r in runs(docs, document.id)] == [RunStatus.ATIVA]


def test_replace_with_a_swapped_extension_gives_422(docs):
    w = docs.world
    document, _ = processed(docs, "extensao")

    with pytest.raises(ValidationFailed) as error:
        docs.replace.execute(
            w.docente, document.id, docs.incoming(synth.png_with_text(), "falso.pdf")
        )

    assert error.value.field == "arquivo"


def test_replace_with_a_file_already_in_the_process_gives_409_with_its_id(docs):
    w = docs.world
    document, _ = processed(docs, "um")
    other, _ = processed(docs, "dois", name="dois.pdf")

    with pytest.raises(DuplicateDocument) as error:
        docs.replace.execute(w.docente, document.id, docs.incoming(pdf("dois")))

    assert isinstance(error.value, Conflict)
    assert error.value.existing_id == other.id
    assert reload(docs, document.id) == document


@pytest.mark.parametrize("status", [DocumentStatus.PENDENTE, DocumentStatus.PROCESSANDO])
def test_replace_of_a_document_still_in_the_queue_gives_409(docs, status):
    w = docs.world
    document = docs.upload_one(w.docente, w.process, pdf("fila"))
    if status is DocumentStatus.PROCESSANDO:
        with w.uow_factory() as uow:
            current = uow.documents.get(document.id)
            uow.documents.update(dataclasses.replace(current, status=status), current.version)
            uow.commit()

    with pytest.raises(Conflict):
        docs.replace.execute(w.docente, document.id, docs.incoming(pdf("fila-novo")))

    assert reload(docs, document.id).sha256 == document.sha256


@pytest.mark.parametrize("status", [ProcessStatus.CONCLUIDO, ProcessStatus.ARQUIVADO])
def test_replace_on_a_closed_process_gives_409(docs, add_process, status):
    w = docs.world
    closed = add_process()
    document, _ = processed(docs, "fechado", process=closed)
    with w.uow_factory() as uow:
        process = uow.processes.get(closed.id)
        uow.processes.update(dataclasses.replace(process, status=status), process.version)
        uow.commit()

    with pytest.raises(Conflict):
        docs.replace.execute(w.docente, document.id, docs.incoming(pdf("fechado-novo")))

    assert reload(docs, document.id) == document


def test_replace_without_access_is_not_found(docs):
    w = docs.world
    document, _ = processed(docs, "alheio")

    for actor in (w.other_docente, w.other_secretaria):
        with pytest.raises(NotFound):
            docs.replace.execute(actor, document.id, docs.incoming(pdf("alheio-novo")))
    with pytest.raises(NotFound):
        docs.replace.execute(w.admin, uuid.uuid4(), docs.incoming(pdf("alheio-novo")))


def test_failure_before_the_commit_keeps_the_old_file_and_drops_the_new_one(docs, stored_files):
    w = docs.world
    document, _ = processed(docs, "falha")
    before_files = stored_files()

    class FailingJobs:
        def add(self, job):
            raise RuntimeError("falha simulada")

    class JobsFail:
        def __init__(self, inner):
            self._inner = inner

        def __enter__(self):
            self._inner.__enter__()
            self._inner.jobs = FailingJobs()
            return self._inner

        def __exit__(self, *exc):
            return self._inner.__exit__(*exc)

    replace = docs.replace_with(uow_factory=lambda: JobsFail(w.uow_factory()))

    with pytest.raises(RuntimeError):
        replace.execute(w.docente, document.id, docs.incoming(pdf("falha-novo")))

    assert reload(docs, document.id) == document
    assert stored_files() == before_files
    assert [r.status for r in runs(docs, document.id)] == [RunStatus.ATIVA]


# --- DeleteDocument ------------------------------------------------------------------------


@pytest.mark.parametrize("justification", [None, "", "   "])
def test_delete_without_justification_gives_422_and_deletes_nothing(docs, justification):
    w = docs.world
    document, _ = processed(docs, "sem-justificativa")

    with pytest.raises(ValidationFailed) as error:
        docs.delete.execute(w.docente, document.id, justification)

    assert error.value.field == "justificativa"
    assert reload(docs, document.id) == document
    assert docs.storage.path(w.process.id, document.internal_name).is_file()


def test_delete_removes_file_text_and_links_but_keeps_the_activities(docs, stored_files):
    w = docs.world
    document, run = processed(docs, "excluir")
    activity = draft_activity(w, w.process, "Banca mantida", run=run)
    link(w, activity, document, page=1, run_id=run.id)

    docs.delete.execute(w.docente, document.id, "Enviado por engano")

    with w.uow_factory() as uow:
        assert uow.documents.get(document.id) is None
        assert uow.extractions.list_runs(document.id) == []
        assert uow.extractions.list_pages(document.id) == []
        assert uow.evidences.list_for_document(document.id) == []
        kept = uow.activities.get(activity.id)
    assert kept is not None and kept.title == "Banca mantida"
    assert kept.status is ActivityStatus.AGUARDANDO_REVISAO
    assert stored_files() == []


def test_delete_audits_user_time_name_hash_and_justification_without_content(docs):
    w = docs.world
    document, run = processed(docs, "auditar-exclusao", name="banca.pdf", texts=("Texto privado",))
    activity = draft_activity(w, w.process, "Atividade", run=run)
    evidence = link(w, activity, document)
    docs.clock.advance(minutes=30)

    docs.delete.execute(w.docente, document.id, "Enviado por engano")

    *_, event = events(docs, "document", document.id)
    assert event.user_id == w.docente.id
    assert event.occurred_at == docs.clock.now()
    assert event.justification == "Enviado por engano"
    assert event.changes["operation"]["after"] == "DELETE"
    assert event.changes["original_name"] == {"before": "banca.pdf", "after": None}
    assert event.changes["sha256"] == {"before": document.sha256, "after": None}
    assert "privado" not in str(event.changes)
    [link_event] = events(docs, "activity_evidence", evidence.id)[-1:]
    assert link_event.user_id == w.docente.id
    assert link_event.changes["operation"]["after"] == "UNLINK"
    assert link_event.justification == "Enviado por engano"


def test_delete_works_for_a_document_still_waiting_in_the_queue(docs):
    w = docs.world
    document = docs.upload_one(w.docente, w.process, pdf("na-fila"))

    docs.delete.execute(w.docente, document.id, "Arquivo errado")

    with w.uow_factory() as uow:
        assert uow.documents.get(document.id) is None
        assert uow.jobs.active_for_document(document.id) is None


def test_delete_when_the_file_is_already_gone_still_succeeds(docs):
    w = docs.world
    document, _ = processed(docs, "sem-arquivo")
    docs.storage.delete(w.process.id, document.internal_name)

    docs.delete.execute(w.docente, document.id, "Limpeza")

    assert reload(docs, document.id) is None


@pytest.mark.parametrize("status", [ProcessStatus.CONCLUIDO, ProcessStatus.ARQUIVADO])
def test_delete_on_a_closed_process_gives_409(docs, add_process, status):
    w = docs.world
    closed = add_process()
    document, _ = processed(docs, "fechado-excluir", process=closed)
    with w.uow_factory() as uow:
        process = uow.processes.get(closed.id)
        uow.processes.update(dataclasses.replace(process, status=status), process.version)
        uow.commit()

    with pytest.raises(Conflict):
        docs.delete.execute(w.docente, document.id, "Tentativa")

    assert reload(docs, document.id) == document
    assert docs.storage.path(closed.id, document.internal_name).is_file()


def test_delete_without_access_is_not_found(docs):
    w = docs.world
    document, _ = processed(docs, "excluir-alheio")

    for actor in (w.other_docente, w.other_secretaria):
        with pytest.raises(NotFound):
            docs.delete.execute(actor, document.id, "Tentativa")
    with pytest.raises(NotFound):
        docs.delete.execute(w.admin, uuid.uuid4(), "Tentativa")
    assert reload(docs, document.id) == document


def test_documents_of_another_process_are_untouched_by_a_deletion(docs, add_process):
    w = docs.world
    other = add_process()
    keep, _ = processed(docs, "mantido", process=other)
    gone, _ = processed(docs, "removido")

    docs.delete.execute(w.docente, gone.id, "Engano")

    assert reload(docs, keep.id) == keep
    assert docs.storage.path(other.id, keep.internal_name).is_file()
