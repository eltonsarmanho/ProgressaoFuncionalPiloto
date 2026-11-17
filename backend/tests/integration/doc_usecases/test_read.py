"""DOC-08, DOC-13, DOC-15, REV-01: GetDocument, ListDocuments and DownloadDocument."""

import dataclasses
import uuid
from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.application.use_cases import documents
from app.domain.entities.audit import AuditAction
from app.domain.entities.document import DocumentStatus, RunStatus, TextMethod
from app.domain.entities.process import ProcessStatus
from app.domain.errors import NotFound, ValidationFailed
from tests.integration.doc_usecases.support import draft_activity, link, pdf, seed_run
from tests.integration.documents.factories import make_document


@pytest.fixture
def read(docs):
    w = docs.world
    return SimpleNamespace(
        get=documents.GetDocument(w.uow_factory, docs.audit, w.policy),
        list=documents.ListDocuments(w.uow_factory, docs.audit, w.policy),
        download=documents.DownloadDocument(w.uow_factory, docs.audit, w.policy, docs.storage),
    )


# --- ListDocuments (DOC-15) ----------------------------------------------------------------


def test_list_is_in_upload_order_with_category_and_confidence(docs, read):
    w = docs.world
    late = docs.clock.now() + timedelta(hours=2)
    early = docs.clock.now() - timedelta(hours=2)
    documents_in_db = [
        make_document(
            w.process, w.admin.id, original_name="tarde.pdf", uploaded_at=late
        ),
        make_document(
            w.process,
            w.admin.id,
            original_name="cedo.pdf",
            uploaded_at=early,
            suggested_type="DECLARACAO_BANCA",
            suggested_category="BANCA_TCC_GRADUACAO",
            confidence=Decimal("0.85"),
        ),
        make_document(
            w.process, w.admin.id, original_name="meio.pdf", uploaded_at=docs.clock.now()
        ),
    ]
    with w.uow_factory() as uow:
        for document in documents_in_db:
            uow.documents.add(document)
        uow.commit()

    listed = read.list.execute(w.docente, w.process.id)

    assert [d.original_name for d in listed] == ["cedo.pdf", "meio.pdf", "tarde.pdf"]
    assert listed[0].suggested_category == "BANCA_TCC_GRADUACAO"
    assert listed[0].confidence == Decimal("0.85")
    assert listed[0].suggested_type == "DECLARACAO_BANCA"


def test_list_filters_by_status_and_by_type(docs, read):
    w = docs.world
    with w.uow_factory() as uow:
        for name, status, suggested, manual in [
            ("a.pdf", DocumentStatus.PROCESSADO, "CERTIFICADO", None),
            ("b.pdf", DocumentStatus.REQUER_REVISAO, "CERTIFICADO", "PORTARIA"),
            ("c.pdf", DocumentStatus.PROCESSADO, "ARTIGO", None),
        ]:
            uow.documents.add(
                make_document(
                    w.process,
                    w.admin.id,
                    original_name=name,
                    status=status,
                    suggested_type=suggested,
                    manual_type=manual,
                )
            )
        uow.commit()

    by_status = read.list.execute(w.admin, w.process.id, status=DocumentStatus.PROCESSADO)
    by_type = read.list.execute(w.admin, w.process.id, type="CERTIFICADO")
    by_manual = read.list.execute(w.admin, w.process.id, type="PORTARIA")
    both = read.list.execute(
        w.admin, w.process.id, status=DocumentStatus.PROCESSADO, type="ARTIGO"
    )

    assert sorted(d.original_name for d in by_status) == ["a.pdf", "c.pdf"]
    assert [d.original_name for d in by_type] == ["a.pdf"]  # b.pdf has the manual type PORTARIA
    assert [d.original_name for d in by_manual] == ["b.pdf"]
    assert [d.original_name for d in both] == ["c.pdf"]


def test_list_only_has_the_documents_of_the_process_and_needs_access(docs, read, add_process):
    w = docs.world
    other = add_process()
    docs.upload_one(w.docente, w.process, pdf("do-processo"))
    docs.upload_one(w.docente, other, pdf("de-outro"))

    assert len(read.list.execute(w.docente, w.process.id)) == 1
    for actor in (w.other_docente, w.other_secretaria):
        with pytest.raises(NotFound):
            read.list.execute(actor, w.process.id)
    with pytest.raises(NotFound):
        read.list.execute(w.admin, uuid.uuid4())


def test_list_works_on_a_closed_process(docs, read, add_process):
    w = docs.world
    closed = add_process(status=ProcessStatus.ARQUIVADO)
    docs.add_documents(closed, w.admin, 2)

    assert len(read.list.execute(w.docente, closed.id)) == 2


# --- GetDocument (REV-01) ------------------------------------------------------------------


def test_detail_has_pages_of_the_active_run_with_method_and_confidence(docs, read):
    w = docs.world
    document = docs.upload_one(w.docente, w.process, pdf("detalhe"))
    seed_run(w, document, status=RunStatus.SUBSTITUIDA, texts=("texto antigo",))
    run = seed_run(w, document, texts=("Primeira pagina", "Segunda pagina"))

    detail = read.get.execute(w.docente, document.id)

    assert detail.document.id == document.id
    assert detail.run.id == run.id
    assert [p.page_number for p in detail.pages] == [1, 2]
    assert [p.method for p in detail.pages] == [TextMethod.TEXTO, TextMethod.OCR]
    assert [p.ocr_confidence for p in detail.pages] == [None, Decimal("88.50")]
    assert [p.text for p in detail.pages] == ["Primeira pagina", "Segunda pagina"]
    assert all(p.run_id == run.id for p in detail.pages)


def test_detail_has_the_raw_json_model_and_alerts_of_the_active_run(docs, read):
    w = docs.world
    document = docs.upload_one(w.docente, w.process, pdf("json"))
    raw = {"document_type": "CERTIFICADO", "activities": []}
    alerts = [{"code": "TRUNCADO", "field": None, "activity_index": None}]
    seed_run(w, document, raw_json=raw, warnings=alerts, model="sabia-4-br-sp")

    detail = read.get.execute(w.docente, document.id)

    assert detail.run.raw_json == raw
    assert detail.run.model == "sabia-4-br-sp"
    assert list(detail.alerts) == alerts


def test_document_never_processed_has_no_run_no_pages_and_no_alerts(docs, read):
    w = docs.world
    document = docs.upload_one(w.docente, w.process, pdf("novo"))

    detail = read.get.execute(w.docente, document.id)

    assert (detail.run, detail.pages, detail.activities) == (None, (), ())
    assert detail.alerts == ()


def test_document_whose_only_run_was_replaced_shows_no_pages(docs, read):
    w = docs.world
    document = docs.upload_one(w.docente, w.process, pdf("substituida"))
    seed_run(w, document, status=RunStatus.SUBSTITUIDA)

    detail = read.get.execute(w.docente, document.id)

    assert detail.run is None
    assert detail.pages == ()


def test_detail_lists_the_linked_activities_with_their_evidence(docs, read):
    w = docs.world
    document = docs.upload_one(w.docente, w.process, pdf("vinculos"), "a.pdf")
    other_document = docs.upload_one(w.docente, w.process, pdf("outro-doc"), "b.pdf")
    run = seed_run(w, document)
    first = draft_activity(w, w.process, "Banca A")
    second = draft_activity(w, w.process, "Banca B")
    unrelated = draft_activity(w, w.process, "Sem vinculo")
    link(w, first, document, page=1, excerpt="trecho A1", run_id=run.id)
    link(w, first, document, page=2, excerpt="trecho A2")
    link(w, second, document, page=2, excerpt="trecho B")
    link(w, unrelated, other_document, page=1)

    detail = read.get.execute(w.docente, document.id)

    by_title = {linked.activity.title: linked for linked in detail.activities}
    assert set(by_title) == {"Banca A", "Banca B"}
    first_links = sorted(by_title["Banca A"].evidences, key=lambda e: e.page_number)
    assert [(e.page_number, e.excerpt, e.document_id) for e in first_links] == [
        (1, "trecho A1", document.id),
        (2, "trecho A2", document.id),
    ]
    assert first_links[0].run_id == run.id
    assert [(e.page_number, e.excerpt) for e in by_title["Banca B"].evidences] == [(2, "trecho B")]


def test_detail_is_not_found_without_access_or_for_an_unknown_document(docs, read):
    w = docs.world
    document = docs.upload_one(w.docente, w.process, pdf("privado"))

    for actor in (w.other_docente, w.other_secretaria):
        with pytest.raises(NotFound):
            read.get.execute(actor, document.id)
    with pytest.raises(NotFound):
        read.get.execute(w.admin, uuid.uuid4())


# --- DownloadDocument (DOC-08, DOC-13) -----------------------------------------------------


def audit_events(docs, document):
    with docs.world.uow_factory() as uow:
        return list(uow.audit.list_for("document", str(document.id)))


def test_download_returns_the_original_as_attachment_and_audits_it(docs, read):
    w = docs.world
    content = pdf("baixar")
    document = docs.upload_one(w.docente, w.process, content, "Minha Banca.pdf")
    docs.clock.advance(minutes=5)

    result = read.download.execute(w.secretaria, document.id, inline=False)

    assert result.path.read_bytes() == content
    assert result.name == "Minha Banca.pdf"
    assert result.mime == "application/pdf"
    assert result.inline is False
    upload, download = audit_events(docs, document)
    assert download.user_id == w.secretaria.id
    assert download.occurred_at == docs.clock.now()
    assert download.action is AuditAction.UPDATE
    assert download.changes == {"operation": {"before": None, "after": "DOWNLOAD"}}
    assert upload.changes["operation"]["after"] == "UPLOAD"


def test_view_is_inline_for_pdf_and_images_and_audits_view(docs, read):
    from tests.support import synthetic_docs as synth

    w = docs.world
    pdf_doc = docs.upload_one(w.docente, w.process, pdf("ver"), "a.pdf")
    image = docs.upload_one(w.docente, w.process, synth.png_with_text(), "b.png")

    shown_pdf = read.download.execute(w.docente, pdf_doc.id, inline=True)
    shown_image = read.download.execute(w.docente, image.id, inline=True)

    assert (shown_pdf.inline, shown_pdf.mime) == (True, "application/pdf")
    assert (shown_image.inline, shown_image.mime) == (True, "image/png")
    assert audit_events(docs, pdf_doc)[-1].changes["operation"]["after"] == "VIEW"


def test_inline_view_of_another_type_is_refused_and_not_audited(docs, read):
    w = docs.world
    docs.add_documents(w.process, w.admin, 1, mime="text/html")
    with w.uow_factory() as uow:
        [odd] = uow.documents.list_for_process(w.process.id)

    with pytest.raises(ValidationFailed) as error:
        read.download.execute(w.admin, odd.id, inline=True)

    assert error.value.field == "visualizar"
    assert audit_events(docs, odd) == []


def test_download_without_access_is_not_found_and_not_audited(docs, read):
    w = docs.world
    document = docs.upload_one(w.docente, w.process, pdf("negado"))

    for actor in (w.other_docente, w.other_secretaria):
        with pytest.raises(NotFound):
            read.download.execute(actor, document.id, inline=False)

    assert len(audit_events(docs, document)) == 1  # only the upload


def test_download_of_a_missing_file_is_not_found(docs, read):
    w = docs.world
    docs.add_documents(w.process, w.admin, 1)
    with w.uow_factory() as uow:
        [ghost] = uow.documents.list_for_process(w.process.id)

    with pytest.raises(NotFound):
        read.download.execute(w.admin, ghost.id, inline=False)


def test_download_works_on_a_closed_process(docs, read, add_process):
    w = docs.world
    document = docs.upload_one(w.docente, w.process, pdf("fechado"))
    with w.uow_factory() as uow:
        process = uow.processes.get(w.process.id)
        uow.processes.update(
            dataclasses.replace(process, status=ProcessStatus.ARQUIVADO), process.version
        )
        uow.commit()

    assert read.download.execute(w.docente, document.id, inline=False).path.is_file()
