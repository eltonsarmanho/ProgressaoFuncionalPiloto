"""DOC-11, DOC-12, DOC-13, PIPE-09 and the concurrent reprocessing edge case."""

import dataclasses
import threading
import uuid

import pytest

from app.application.use_cases.documents import REPROCESS_JUSTIFICATION
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
    pdf,
)

FINAL_STATUSES = [
    DocumentStatus.PROCESSADO,
    DocumentStatus.REQUER_REVISAO,
    DocumentStatus.EXTRAIDO_SEM_IA,
    DocumentStatus.FALHOU,
]


def processed(docs, label, process=None, status=DocumentStatus.PROCESSADO):
    w = docs.world
    document = docs.upload_one(w.docente, process or w.process, pdf(label))
    return finish_processing(w, document, status=status)


def reload(docs, document_id):
    with docs.world.uow_factory() as uow:
        return uow.documents.get(document_id)


def events(docs, entity, entity_id):
    with docs.world.uow_factory() as uow:
        return list(uow.audit.list_for(entity, str(entity_id)))


def close_process(docs, process, status):
    with docs.world.uow_factory() as uow:
        current = uow.processes.get(process.id)
        uow.processes.update(dataclasses.replace(current, status=status), current.version)
        uow.commit()


# --- ClassifyDocumentManually (DOC-11) ----------------------------------------------------


def test_manual_classification_is_stored_without_erasing_the_suggested_one(docs):
    w = docs.world
    document, _ = processed(docs, "classificar")
    with w.uow_factory() as uow:
        current = uow.documents.get(document.id)
        uow.documents.update(
            dataclasses.replace(
                current,
                suggested_type="DECLARACAO_BANCA",
                suggested_category="BANCA_TCC_GRADUACAO",
                confidence=None,
            ),
            current.version,
        )
        uow.commit()

    result = docs.classify.execute(w.docente, document.id, "CERTIFICADO", "CURSO_CONCLUIDO")

    current = reload(docs, document.id)
    assert (current.manual_type, current.manual_category) == ("CERTIFICADO", "CURSO_CONCLUIDO")
    assert (current.suggested_type, current.suggested_category) == (
        "DECLARACAO_BANCA",
        "BANCA_TCC_GRADUACAO",
    )
    assert current.status is DocumentStatus.PROCESSADO
    assert result.manual_type == "CERTIFICADO"


def test_manual_classification_audits_user_time_document_and_operation(docs):
    w = docs.world
    document, _ = processed(docs, "audit-classificar")
    docs.clock.advance(minutes=10)

    docs.classify.execute(w.secretaria, document.id, "PORTARIA", "FUNCAO_DIRETOR_FACULDADE")

    *_, event = events(docs, "document", document.id)
    assert event.user_id == w.secretaria.id
    assert event.occurred_at == docs.clock.now()
    assert event.action is AuditAction.UPDATE
    assert event.changes == {
        "manual_type": {"before": None, "after": "PORTARIA"},
        "manual_category": {"before": None, "after": "FUNCAO_DIRETOR_FACULDADE"},
        "operation": {"before": None, "after": "CLASSIFY"},
    }


def test_manual_classification_may_be_changed_again(docs):
    w = docs.world
    document, _ = processed(docs, "reclassificar")
    docs.classify.execute(w.docente, document.id, "PORTARIA", "OUTRA")

    docs.classify.execute(w.docente, document.id, "ARTIGO", "ARTIGO_NAO_INDEXADO")

    current = reload(docs, document.id)
    assert (current.manual_type, current.manual_category) == ("ARTIGO", "ARTIGO_NAO_INDEXADO")


@pytest.mark.parametrize(
    ("document_type", "category", "field"),
    [
        ("INVENTADO", "OUTRA", "tipo"),
        ("", "OUTRA", "tipo"),
        (None, "OUTRA", "tipo"),
        ("CERTIFICADO", "INVENTADA", "categoria"),
        ("CERTIFICADO", "", "categoria"),
        ("CERTIFICADO", None, "categoria"),
    ],
)
def test_invalid_manual_classification_gives_422_on_the_field(
    docs, document_type, category, field
):
    w = docs.world
    document, _ = processed(docs, "invalida")

    with pytest.raises(ValidationFailed) as error:
        docs.classify.execute(w.docente, document.id, document_type, category)

    assert error.value.field == field
    assert reload(docs, document.id).manual_type is None


@pytest.mark.parametrize("status", [ProcessStatus.CONCLUIDO, ProcessStatus.ARQUIVADO])
def test_classification_on_a_closed_process_gives_409(docs, add_process, status):
    w = docs.world
    closed = add_process()
    document, _ = processed(docs, "fechado-classif", process=closed)
    close_process(docs, closed, status)

    with pytest.raises(Conflict):
        docs.classify.execute(w.docente, document.id, "CERTIFICADO", "OUTRA")

    assert reload(docs, document.id).manual_type is None


def test_classification_without_access_is_not_found(docs):
    w = docs.world
    document, _ = processed(docs, "alheio-classif")

    for actor in (w.other_docente, w.other_secretaria):
        with pytest.raises(NotFound):
            docs.classify.execute(actor, document.id, "CERTIFICADO", "OUTRA")
    with pytest.raises(NotFound):
        docs.classify.execute(w.admin, uuid.uuid4(), "CERTIFICADO", "OUTRA")


# --- ReprocessDocument (PIPE-09) ----------------------------------------------------------


@pytest.mark.parametrize("status", FINAL_STATUSES)
def test_reprocess_queues_a_new_job_and_retires_the_active_run(docs, status):
    w = docs.world
    document, run = processed(docs, f"reprocessar-{status}", status=status)

    result = docs.reprocess.execute(w.docente, document.id)

    assert result.status is DocumentStatus.PENDENTE
    assert reload(docs, document.id).status is DocumentStatus.PENDENTE
    with w.uow_factory() as uow:
        job = uow.jobs.active_for_document(document.id)
        runs = list(uow.extractions.list_runs(document.id))
    assert job.status is JobStatus.PENDENTE
    assert [(r.id, r.status) for r in runs] == [(run.id, RunStatus.SUBSTITUIDA)]


def test_reprocess_rejects_untouched_drafts_and_keeps_validated_or_edited_ones(docs):
    w = docs.world
    document, run = processed(docs, "rascunhos-reprocesso")
    _, other_run = processed(docs, "outro-reprocesso")
    untouched = draft_activity(w, w.process, "Intocada", run=run)
    edited = draft_activity(w, w.process, "Editada", run=run)
    w.update.execute(
        w.admin,
        edited.id,
        ActivityData(title="Editada pelo usuario", group_number=3, item_number=4),
        edited.version,
        None,
    )
    validated = draft_activity(w, w.process, "Validada", run=run)
    w.change_status.execute(
        w.admin, validated.id, ActivityStatus.VALIDADA, validated.version, "Conferida"
    )
    rejected_before = draft_activity(w, w.process, "Ja rejeitada", run=run)
    w.change_status.execute(
        w.admin, rejected_before.id, ActivityStatus.REJEITADA, rejected_before.version, "Erro"
    )
    draft_activity(w, w.process, "De outro documento", run=other_run)
    w.create.execute(w.admin, w.process.id, ActivityData(title="Manual"))

    docs.reprocess.execute(w.secretaria, document.id)

    with w.uow_factory() as uow:
        by_title = {a.title: a for a in uow.activities.list_for_process(w.process.id)}
        audit = uow.audit.list_for("activity", str(untouched.id))
    assert by_title["Intocada"].status is ActivityStatus.REJEITADA
    assert by_title["Editada pelo usuario"].status is ActivityStatus.AGUARDANDO_REVISAO
    assert by_title["Validada"].status is ActivityStatus.VALIDADA
    assert by_title["Ja rejeitada"].status is ActivityStatus.REJEITADA
    assert by_title["De outro documento"].status is ActivityStatus.AGUARDANDO_REVISAO
    assert by_title["Manual"].status is ActivityStatus.VALIDADA
    [created, rejection] = audit
    assert rejection.action is AuditAction.STATUS
    assert rejection.justification == REPROCESS_JUSTIFICATION == (
        "Substituída por reprocessamento do documento"
    )
    assert rejection.user_id == w.secretaria.id
    assert rejection.changes == {
        "status": {"before": "AGUARDANDO_REVISAO", "after": "REJEITADA"}
    }
    assert created.action is AuditAction.CREATE


def test_reprocess_audits_user_time_document_and_operation(docs):
    w = docs.world
    document, _ = processed(docs, "audit-reprocesso")
    docs.clock.advance(hours=2)

    docs.reprocess.execute(w.docente, document.id)

    *_, event = events(docs, "document", document.id)
    assert event.user_id == w.docente.id
    assert event.occurred_at == docs.clock.now()
    assert event.action is AuditAction.STATUS
    assert event.changes == {
        "status": {"before": "PROCESSADO", "after": "PENDENTE"},
        "operation": {"before": None, "after": "REPROCESS"},
    }


@pytest.mark.parametrize("status", [DocumentStatus.PENDENTE, DocumentStatus.PROCESSANDO])
def test_reprocess_of_a_document_in_the_queue_gives_409_and_changes_nothing(docs, status):
    w = docs.world
    document, run = processed(docs, f"fila-{status}")
    draft = draft_activity(w, w.process, "Rascunho", run=run)
    docs.reprocess.execute(w.docente, document.id)  # now PENDENTE with an active job
    if status is DocumentStatus.PROCESSANDO:
        with w.uow_factory() as uow:
            current = uow.documents.get(document.id)
            uow.documents.update(dataclasses.replace(current, status=status), current.version)
            uow.commit()
    with w.uow_factory() as uow:
        jobs_before = uow.jobs.active_for_document(document.id)

    with pytest.raises(Conflict):
        docs.reprocess.execute(w.docente, document.id)

    with w.uow_factory() as uow:
        assert uow.jobs.active_for_document(document.id) == jobs_before
        assert len(uow.audit.list_for("activity", str(draft.id))) == 2  # created + one rejection


def test_second_reprocess_request_gets_409_and_the_first_one_stands(docs):
    w = docs.world
    document, _ = processed(docs, "duas-solicitacoes")

    first = docs.reprocess.execute(w.docente, document.id)
    with pytest.raises(Conflict):
        docs.reprocess.execute(w.secretaria, document.id)

    assert first.status is DocumentStatus.PENDENTE
    reprocess_events = [
        e
        for e in events(docs, "document", document.id)
        if e.changes.get("operation", {}).get("after") == "REPROCESS"
    ]
    assert [e.user_id for e in reprocess_events] == [w.docente.id]


def test_two_simultaneous_reprocess_requests_accept_exactly_one(docs):
    w = docs.world
    document, run = processed(docs, "simultaneas")
    draft = draft_activity(w, w.process, "Rascunho", run=run)
    barrier = threading.Barrier(2)
    outcomes = []

    def request(actor):
        barrier.wait()
        try:
            docs.reprocess.execute(actor, document.id)
            outcomes.append("ok")
        except Conflict:
            outcomes.append("conflict")

    threads = [threading.Thread(target=request, args=(a,)) for a in (w.docente, w.secretaria)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)

    assert sorted(outcomes) == ["conflict", "ok"]
    with w.uow_factory() as uow:
        assert uow.jobs.active_for_document(document.id).status is JobStatus.PENDENTE
        assert uow.activities.get(draft.id).status is ActivityStatus.REJEITADA
        assert len(uow.audit.list_for("activity", str(draft.id))) == 2


def test_reprocess_of_a_failed_document_without_any_run_works(docs):
    w = docs.world
    document = docs.upload_one(w.docente, w.process, pdf("sem-execucao"))
    with w.uow_factory() as uow:
        job = uow.jobs.claim_next(docs.clock.now())
        uow.jobs.finish(job.id, JobStatus.FALHOU, docs.clock.now(), "ERRO_INTERNO")
        current = uow.documents.get(document.id)
        uow.documents.update(
            dataclasses.replace(current, status=DocumentStatus.FALHOU), current.version
        )
        uow.commit()

    result = docs.reprocess.execute(w.docente, document.id)

    assert result.status is DocumentStatus.PENDENTE


@pytest.mark.parametrize("status", [ProcessStatus.CONCLUIDO, ProcessStatus.ARQUIVADO])
def test_reprocess_on_a_closed_process_gives_409(docs, add_process, status):
    w = docs.world
    closed = add_process()
    document, run = processed(docs, "fechado-reprocesso", process=closed)
    close_process(docs, closed, status)

    with pytest.raises(Conflict):
        docs.reprocess.execute(w.docente, document.id)

    assert reload(docs, document.id).status is DocumentStatus.PROCESSADO


def test_reprocess_without_access_is_not_found(docs):
    w = docs.world
    document, _ = processed(docs, "alheio-reprocesso")

    for actor in (w.other_docente, w.other_secretaria):
        with pytest.raises(NotFound):
            docs.reprocess.execute(actor, document.id)
    with pytest.raises(NotFound):
        docs.reprocess.execute(w.admin, uuid.uuid4())
    assert reload(docs, document.id).status is DocumentStatus.PROCESSADO
