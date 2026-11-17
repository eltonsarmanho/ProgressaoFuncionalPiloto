"""PIPE-01, PIPE-02, PIPE-03, PIPE-10, PIPE-11, VINC-01, CLS-08: ProcessDocument."""

import logging
import uuid
from datetime import date
from decimal import Decimal

import pytest

from app.application.services.document_analyzer import DocumentAnalyzer
from app.application.use_cases import document_processing
from app.application.use_cases.scoring import ActivityData
from app.domain.entities.activity import ActivitySource, ActivityStatus
from app.domain.entities.audit import AuditAction
from app.domain.entities.document import DocAlertCode, DocumentStatus, RunStatus, TextMethod
from app.domain.errors import NotFound
from app.domain.repositories.ports import AiExtractionError, JobStatus
from app.domain.rules.interstice import Interstice
from app.domain.rules.upload_validation import FileKind
from tests.integration.doc_usecases.support import pdf
from tests.unit.application.analyzer_fakes import (
    FakeAi,
    FakeTextExtractor,
    StepClock,
    activity,
    ocr_page,
    payload,
    text_page,
)


def banca_text(w) -> str:
    return (
        "DECLARACAO DE BANCA EXAMINADORA\n"
        f"Declaramos que {w.professor.full_name}, matricula SIAPE {w.professor.siape}, "
        "participou como membro da banca examinadora do trabalho de conclusao de curso "
        "Estudo Ficticio sobre Dados Abertos, realizada em 12 de marco de 2023, "
        "na Faculdade Exemplo de Testes."
    )


def banca_payload(w, **changes):
    return payload(activity(event_date="2023-03-12", **changes), name=w.professor.full_name)


def course(title, hours, period, level, confidence=0.95):
    return activity(
        taxonomy="DISCIPLINA_MINISTRADA",
        title=title,
        role=None,
        event_date=None,
        hours=hours,
        academic_period=period,
        level=level,
        evidence_text=f"{period} {title}",
        confidence=confidence,
    )


def disciplinas_text(w) -> str:
    return (
        "DECLARACAO DE COMPONENTES CURRICULARES\n"
        f"Declaramos que {w.professor.full_name} ministrou os componentes curriculares abaixo.\n"
        "2023/1 Algoritmos e Programacao Graduacao CH Docente 60 horas\n"
        "2023/1 Mineracao de Dados Pos-Graduacao CH Docente 45 horas\n"
        "2023/2 Banco de Dados Graduacao CH Docente 30 horas"
    )


def submit(docs, label="banca", actor=None, process=None):
    w = docs.world
    return docs.upload_one(actor or w.docente, process or w.process, pdf(label))


def process_banca(docs, label="banca", ai=None, text=None, actor=None):
    """Upload a document and run its job with a fake extractor and a fake AI."""
    w = docs.world
    document = submit(docs, label, actor)
    extractor = FakeTextExtractor(text_page(1, text or banca_text(w)))
    use_case = docs.processor(extractor, ai or FakeAi(banca_payload(w)))
    docs.run_next_job(use_case)
    return document


def state(docs, document):
    """(document, runs, pages, activities, evidences, job) as stored."""
    with docs.world.uow_factory() as uow:
        return SimpleState(
            document=uow.documents.get(document.id),
            runs=list(uow.extractions.list_runs(document.id)),
            pages=list(uow.extractions.list_pages(document.id)),
            activities=list(uow.activities.list_for_process(document.process_id)),
            evidences=list(uow.evidences.list_for_document(document.id)),
        )


class SimpleState:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


# --- the document of a banca ---------------------------------------------------------------


def test_banca_document_becomes_a_processed_document_with_a_draft_activity(docs):
    w = docs.world
    document = process_banca(docs)

    found = state(docs, document)

    assert found.document.status is DocumentStatus.PROCESSADO
    assert found.document.status_code is None
    assert found.document.suggested_type == "DECLARACAO_BANCA"
    assert found.document.suggested_category == "BANCA_TCC_GRADUACAO"
    assert found.document.confidence == Decimal("0.95")
    [created] = found.activities
    assert created.source is ActivitySource.SUGERIDA_IA
    assert created.status is ActivityStatus.AGUARDANDO_REVISAO
    assert (created.group_number, created.item_number) == (3, 4)
    assert created.title == "Estudo Ficticio sobre Dados Abertos"
    assert created.event_date == date(2023, 3, 12)
    assert created.created_by == w.docente.id
    assert created.candidates == ()
    [run] = found.runs
    assert created.extraction_run_id == run.id


def test_the_draft_is_linked_to_document_page_and_excerpt(docs):
    w = docs.world
    document = process_banca(docs)

    found = state(docs, document)

    [evidence] = found.evidences
    [created] = found.activities
    [run] = found.runs
    assert (evidence.activity_id, evidence.document_id) == (created.id, document.id)
    assert evidence.page_number == 1
    assert evidence.run_id == run.id
    assert evidence.created_by == w.docente.id
    assert evidence.excerpt == "participou como membro da banca examinadora"
    assert len(evidence.excerpt) <= 300
    with w.uow_factory() as uow:
        [event] = uow.audit.list_for("activity_evidence", str(evidence.id))
    assert event.action is AuditAction.CREATE
    assert event.user_id == w.docente.id
    assert event.changes["operation"]["after"] == "LINK"
    assert "banca" not in str(event.changes)


def test_excerpt_is_cut_at_300_characters(docs):
    w = docs.world
    long_page = banca_text(w) + " " + "palavra " * 200
    document = process_banca(
        docs,
        ai=FakeAi(banca_payload(w, evidence_text="trecho que nao esta na pagina")),
        text=long_page,
    )

    [evidence] = state(docs, document).evidences

    assert 0 < len(evidence.excerpt) <= 300
    assert " ".join(long_page.split()).startswith(evidence.excerpt)


def test_run_stores_raw_json_model_duration_warnings_and_unmasked_pages(docs):
    w = docs.world
    cpf_page = banca_text(w) + " CPF 123.456.789-09."
    ai_payload = banca_payload(w)
    document = process_banca(docs, ai=FakeAi(ai_payload, model="sabia-fake"), text=cpf_page)

    found = state(docs, document)

    [run] = found.runs
    assert run.status is RunStatus.ATIVA
    assert run.raw_json == ai_payload
    assert run.model == "sabia-fake"
    assert run.duration_ms == 1500
    assert run.warnings == ()
    [page] = found.pages
    assert (page.page_number, page.method, page.run_id) == (1, TextMethod.TEXTO, run.id)
    assert page.text == cpf_page  # the original text, without the AI mask
    assert page.char_count == len(cpf_page)


def test_ocr_page_keeps_its_method_and_confidence(docs):
    w = docs.world
    document = submit(docs, "ocr")
    extractor = FakeTextExtractor(ocr_page(1, banca_text(w), "87.50"))
    docs.run_next_job(docs.processor(extractor, FakeAi(banca_payload(w))))

    [page] = state(docs, document).pages

    assert (page.method, page.ocr_confidence) == (TextMethod.OCR, Decimal("87.50"))


def test_activities_are_created_as_the_uploader_with_their_own_audit(docs):
    w = docs.world
    document = process_banca(docs, "secretaria", actor=w.secretaria)

    [created] = state(docs, document).activities

    assert created.created_by == w.secretaria.id
    with w.uow_factory() as uow:
        [event] = uow.audit.list_for("activity", str(created.id))
    assert (event.user_id, event.action) == (w.secretaria.id, AuditAction.CREATE)


def test_job_is_concluded_and_no_activity_is_validated_by_itself(docs):
    w = docs.world
    document = submit(docs, "concluida")
    extractor = FakeTextExtractor(text_page(1, banca_text(w)))
    job = docs.run_next_job(docs.processor(extractor, FakeAi(banca_payload(w))))

    with w.uow_factory() as uow:
        finished = uow.jobs.get(job.id)
        assert uow.jobs.active_for_document(document.id) is None
    assert finished.status is JobStatus.CONCLUIDA
    assert finished.finished_at == docs.clock.now()
    assert finished.error_code is None
    statuses = [a.status for a in state(docs, document).activities]
    assert statuses == [ActivityStatus.AGUARDANDO_REVISAO]


# --- what the analyzer receives ------------------------------------------------------------


class SpyAnalyzer(DocumentAnalyzer):
    def __init__(self, *args):
        super().__init__(*args)
        self.calls = []

    def analyze(self, *args):
        self.calls.append(args)
        return super().analyze(*args)


def banca_spy(w) -> SpyAnalyzer:
    extractor = FakeTextExtractor(text_page(1, banca_text(w)))
    return SpyAnalyzer(extractor, FakeAi(banca_payload(w)), StepClock())


def test_analyzer_gets_the_file_the_professor_the_interstice_and_the_chosen_table(docs):
    w = docs.world
    w.choose.execute(w.admin, w.process.id, w.fasi_version.id, None, None)
    document = submit(docs, "args")
    spy = banca_spy(w)

    docs.run_next_job(docs.processor(None, None, analyzer=spy))

    [(path, kind, name, siape, interstice, version)] = spy.calls
    assert path == docs.storage.path(w.process.id, document.internal_name)
    assert kind is FileKind.PDF
    assert (name, siape) == (w.professor.full_name, w.professor.siape)
    assert interstice == Interstice(w.process.start_date, w.process.end_date)
    assert version.id == w.fasi_version.id


def test_analyzer_gets_no_table_when_the_process_has_none(docs):
    w = docs.world
    submit(docs, "sem-tabela")
    spy = banca_spy(w)

    docs.run_next_job(docs.processor(None, None, analyzer=spy))

    assert spy.calls[0][5] is None


# --- several activities, no item, AI down --------------------------------------------------


def test_course_declaration_creates_one_group_i_activity_per_offer(docs):
    w = docs.world
    offers = [
        course("Algoritmos e Programacao", 60, "2023/1", "GRADUACAO", 0.95),
        course("Mineracao de Dados", 45, "2023/1", "POS_GRADUACAO", 0.80),
        course("Banco de Dados", 30, "2023/2", "GRADUACAO", 0.90),
    ]
    document = submit(docs, "disciplinas")
    extractor = FakeTextExtractor(text_page(1, disciplinas_text(w)))
    ai = FakeAi(
        payload(*offers, name=w.professor.full_name, document_type="DECLARACAO_DISCIPLINAS")
    )
    docs.run_next_job(docs.processor(extractor, ai))

    found = state(docs, document)

    got = sorted(
        (a.academic_period, a.group_number, a.item_number, a.level.value, a.hours)
        for a in found.activities
    )
    assert got == [
        ("2023.1", 1, 1, "GRADUACAO", Decimal("60")),
        ("2023.1", 1, 2, "POS_GRADUACAO", Decimal("45")),
        ("2023.2", 1, 1, "GRADUACAO", Decimal("30")),
    ]
    assert all(a.status is ActivityStatus.AGUARDANDO_REVISAO for a in found.activities)
    assert len(found.evidences) == 3
    assert {e.activity_id for e in found.evidences} == {a.id for a in found.activities}
    assert found.document.suggested_category == "DISCIPLINA_MINISTRADA"
    assert found.document.confidence == Decimal("0.80")  # the lowest of the activities


def test_document_without_a_scoring_item_is_processed_with_no_activity_and_the_warning(docs):
    w = docs.world
    document = process_banca(
        docs, ai=FakeAi(banca_payload(w, taxonomy="COORIENTACAO_TCC_GRADUACAO"))
    )

    found = state(docs, document)

    assert found.document.status is DocumentStatus.PROCESSADO
    assert found.activities == []
    assert found.evidences == []
    assert found.document.suggested_category == "SEM_ITEM_DE_PONTUACAO"
    assert found.document.confidence is None
    assert list(found.runs[0].warnings) == [
        {"code": "SEM_ITEM_DE_PONTUACAO", "field": None, "activity_index": 0}
    ]
    assert len(found.pages) == 1  # the text stays available to create the activity by hand


@pytest.mark.parametrize(
    "code", [DocAlertCode.IA_INDISPONIVEL, DocAlertCode.IA_CREDENCIAL_RECUSADA]
)
def test_ai_unavailable_ends_extracted_without_ai_and_manual_entry_keeps_working(docs, code):
    w = docs.world
    document = process_banca(docs, ai=FakeAi(AiExtractionError(code)))

    found = state(docs, document)
    manual = w.create.execute(w.docente, w.process.id, ActivityData(title="Cadastro manual"))

    assert found.document.status is DocumentStatus.EXTRAIDO_SEM_IA
    assert found.document.status_code == code.value
    assert found.activities == []
    assert len(found.pages) == 1
    [run] = found.runs
    assert run.raw_json == {} and run.model == ""
    assert [w_["code"] for w_ in run.warnings] == [code.value]
    assert manual.status is ActivityStatus.VALIDADA


def test_unreadable_text_requires_review_and_suggests_nothing(docs):
    w = docs.world
    document = submit(docs, "ilegivel")
    docs.run_next_job(docs.processor(FakeTextExtractor(text_page(1, "")), FakeAi(banca_payload(w))))

    found = state(docs, document)

    assert found.document.status is DocumentStatus.REQUER_REVISAO
    assert found.document.status_code == "TEXTO_ILEGIVEL"
    assert found.document.suggested_type is None
    assert found.activities == []


def test_timeout_fails_the_document_keeping_the_pages_already_read(docs):
    w = docs.world
    document = submit(docs, "tempo")
    extractor = FakeTextExtractor(text_page(1, banca_text(w)), timed_out=True)
    job = docs.run_next_job(docs.processor(extractor, FakeAi(banca_payload(w))))

    found = state(docs, document)

    assert found.document.status is DocumentStatus.FALHOU
    assert found.document.status_code == "TEMPO_ESGOTADO"
    assert len(found.pages) == 1
    with docs.world.uow_factory() as uow:
        finished = uow.jobs.get(job.id)
    assert (finished.status, finished.error_code) == (JobStatus.FALHOU, "TEMPO_ESGOTADO")


def test_foreign_teacher_requires_review_but_keeps_the_draft(docs):
    w = docs.world
    other = "Beltrano de Outra Pessoa"
    foreign_text = banca_text(w).replace(w.professor.full_name, other)
    foreign_text = foreign_text.replace(w.professor.siape, "9999999")
    ai = FakeAi(payload(activity(event_date="2023-03-12"), name=other))
    document = process_banca(docs, ai=ai, text=foreign_text)

    found = state(docs, document)

    assert found.document.status is DocumentStatus.REQUER_REVISAO
    assert [x["code"] for x in found.runs[0].warnings] == ["DOCENTE_DIVERGENTE"]
    assert len(found.activities) == 1


# --- activities the scoring rules would refuse ---------------------------------------------


def test_suggestion_without_a_title_still_gives_a_draft_with_a_title(docs):
    w = docs.world
    document = process_banca(docs, ai=FakeAi(banca_payload(w, title=None)))

    [created] = state(docs, document).activities

    assert created.title.strip()
    assert (created.group_number, created.item_number) == (3, 4)


def test_group_i_suggestion_without_a_level_is_kept_unclassified_and_linked(docs):
    w = docs.world
    document = submit(docs, "sem-nivel")
    extractor = FakeTextExtractor(text_page(1, disciplinas_text(w)))
    offer = course("Algoritmos e Programacao", 60, "2023/1", None)
    ai = FakeAi(payload(offer, name=w.professor.full_name, document_type="DECLARACAO_DISCIPLINAS"))
    docs.run_next_job(docs.processor(extractor, ai))

    found = state(docs, document)

    [created] = found.activities
    assert created.status is ActivityStatus.AGUARDANDO_REVISAO
    assert created.source is ActivitySource.SUGERIDA_IA
    assert (created.group_number, created.item_number) == (None, None)
    assert created.title == "Algoritmos e Programacao"
    assert [e.activity_id for e in found.evidences] == [created.id]


# --- reprocessing --------------------------------------------------------------------------


def test_second_run_replaces_the_first_one_and_its_untouched_drafts(docs):
    w = docs.world
    document = process_banca(docs)
    docs.clock.advance(minutes=5)
    docs.reprocess.execute(w.docente, document.id)
    second_ai = FakeAi(banca_payload(w, title="Outro Titulo Ficticio"))
    docs.run_next_job(docs.processor(FakeTextExtractor(text_page(1, banca_text(w))), second_ai))

    found = state(docs, document)

    first_run, second_run = found.runs
    assert (first_run.status, second_run.status) == (RunStatus.SUBSTITUIDA, RunStatus.ATIVA)
    assert [p.run_id for p in found.pages] == [second_run.id]
    by_run = {a.extraction_run_id: a for a in found.activities}
    assert by_run[first_run.id].status is ActivityStatus.REJEITADA
    assert by_run[second_run.id].status is ActivityStatus.AGUARDANDO_REVISAO
    assert found.document.status is DocumentStatus.PROCESSADO


# --- failures and logs ---------------------------------------------------------------------


class Exploding(DocumentAnalyzer):
    def __init__(self, error):
        self._error = error

    def analyze(self, *args):
        raise self._error


def test_unexpected_exception_fails_the_document_with_erro_interno(docs, caplog):
    document = submit(docs, "explode")
    caplog.set_level(logging.DEBUG)

    job = docs.run_next_job(
        docs.processor(None, None, analyzer=Exploding(RuntimeError("Texto secreto do documento")))
    )

    found = state(docs, document)
    assert found.document.status is DocumentStatus.FALHOU
    assert found.document.status_code == "ERRO_INTERNO"
    with docs.world.uow_factory() as uow:
        finished = uow.jobs.get(job.id)
    assert (finished.status, finished.error_code) == (JobStatus.FALHOU, "ERRO_INTERNO")
    logged = " ".join(r.getMessage() for r in caplog.records)
    assert "RuntimeError" in logged
    assert "secreto" not in logged
    assert all(r.exc_info is None for r in caplog.records)


def test_logs_have_identifiers_methods_duration_pages_and_codes_but_no_content(docs, caplog):
    w = docs.world
    caplog.set_level(logging.DEBUG)

    document = process_banca(docs, "logs")

    logged = " ".join(r.getMessage() for r in caplog.records)
    for forbidden in (
        w.professor.full_name,
        w.professor.siape,
        "Estudo Ficticio",
        "participou",
        "Faculdade",
        "declaracao.pdf",
        "12 de marco",
    ):
        assert forbidden not in logged
    line = next(r.getMessage() for r in caplog.records if "pages=" in r.getMessage())
    assert f"document_id={document.id}" in line
    assert "status=PROCESSADO" in line
    assert "pages=1" in line
    assert "TEXTO" in line
    assert "duration_ms=1500" in line


# --- recovery and edge cases ---------------------------------------------------------------


class Crash(BaseException):
    """Stands for the process dying in the middle of a job."""


def test_stuck_jobs_go_back_to_pending_and_are_processed_after_the_restart(docs):
    w = docs.world
    document = submit(docs, "reinicio")
    with pytest.raises(Crash):
        docs.run_next_job(docs.processor(None, None, analyzer=Exploding(Crash())))
    with w.uow_factory() as uow:
        assert uow.jobs.active_for_document(document.id).status is JobStatus.PROCESSANDO
        assert uow.documents.get(document.id).status is DocumentStatus.PROCESSANDO

    recovered = document_processing.RecoverStuckJobs(w.uow_factory).execute()

    assert recovered == 1
    with w.uow_factory() as uow:
        assert uow.jobs.active_for_document(document.id).status is JobStatus.PENDENTE
    docs.run_next_job(
        docs.processor(FakeTextExtractor(text_page(1, banca_text(w))), FakeAi(banca_payload(w)))
    )
    assert state(docs, document).document.status is DocumentStatus.PROCESSADO


def test_recovering_with_nothing_stuck_changes_nothing(docs):
    w = docs.world
    submit(docs, "nada")

    assert document_processing.RecoverStuckJobs(w.uow_factory).execute() == 0


def test_document_deleted_while_it_is_processed_is_dropped_quietly(docs):
    w = docs.world
    document = submit(docs, "apagado")

    class DeletesWhileRunning(DocumentAnalyzer):
        def __init__(self):
            pass

        def analyze(self, *args):
            docs.delete.execute(w.docente, document.id, "Enviado por engano")
            return banca_spy(w).analyze(*args)

    docs.run_next_job(docs.processor(None, None, analyzer=DeletesWhileRunning()))

    with w.uow_factory() as uow:
        assert uow.documents.get(document.id) is None
        assert uow.activities.list_for_process(w.process.id) == []


def test_unknown_job_is_not_found(docs):
    use_case = docs.processor(FakeTextExtractor(), FakeAi({}))

    with pytest.raises(NotFound):
        use_case.execute(uuid.uuid4(), docs.clock.now())
