"""DEL-12, DEL-06: a document whose file was removed by the conclusion answers `Gone`
(ARQUIVO_EXCLUIDO) when its file, its page text, a reprocessing or a replacement is asked; its
metadata and its links still show."""

import dataclasses
import uuid
from types import SimpleNamespace

import pytest

from app.application.services.purge_inputs import PurgeInputDocuments
from app.application.use_cases import documents
from app.domain.entities.process import ProcessStatus
from app.domain.errors import Gone, NotFound
from tests.integration.doc_usecases.support import draft_activity, finish_processing, link, pdf
from tests.integration.doc_usecases.test_purge_inputs import FixedClock


@pytest.fixture
def case(docs):
    """A processed document with two pages of text and one link, and the same use cases bound to
    the storage; `purge()` removes the input documents of the process as the conclusion does."""
    w = docs.world
    document = docs.upload_one(w.docente, w.process, pdf("excluivel", pages=2))
    document, run = finish_processing(w, document)
    activity = draft_activity(w, w.process, "Banca", run=run)
    evidence = link(w, activity, document, page=2, excerpt="trecho da banca", run_id=run.id)

    def purge():
        PurgeInputDocuments(w.uow_factory, docs.storage, FixedClock()).execute(w.process.id)

    def conclude_process():
        with w.uow_factory() as uow:
            current = uow.processes.get(w.process.id)
            uow.processes.update(
                dataclasses.replace(current, status=ProcessStatus.CONCLUIDO), current.version
            )
            uow.commit()

    return SimpleNamespace(
        docs=docs,
        world=w,
        document=document,
        evidence=evidence,
        purge=purge,
        conclude_process=conclude_process,
        get=documents.GetDocument(w.uow_factory, docs.audit, w.policy),
        listing=documents.ListDocuments(w.uow_factory, docs.audit, w.policy),
        download=documents.DownloadDocument(w.uow_factory, docs.audit, w.policy, docs.storage),
    )


def test_a_common_document_still_downloads_and_shows_its_pages(case):
    w = case.world

    detail = case.get.execute(w.docente, case.document.id)
    downloaded = case.download.execute(w.docente, case.document.id, inline=False)

    assert [p.text for p in detail.pages] == ["Texto da pagina um", "Texto da pagina dois"]
    assert detail.file_deleted is False
    assert downloaded.path.is_file()


@pytest.mark.parametrize("inline", [False, True])
def test_the_file_of_a_deleted_document_is_gone(case, inline):
    case.purge()

    with pytest.raises(Gone) as error:
        case.download.execute(case.world.docente, case.document.id, inline=inline)

    assert error.value.code == "ARQUIVO_EXCLUIDO"


def test_the_detail_of_a_deleted_document_has_the_metadata_the_links_and_no_text(case):
    w = case.world
    case.purge()

    detail = case.get.execute(w.docente, case.document.id)

    assert detail.file_deleted is True
    assert detail.pages == ()
    kept = ("original_name", "mime", "size_bytes", "sha256", "page_count")
    assert all(getattr(detail.document, f) == getattr(case.document, f) for f in kept)
    assert (detail.document.original_name, detail.document.page_count) == ("declaracao.pdf", 2)
    [linked] = detail.activities
    [evidence] = linked.evidences
    assert (evidence.document_id, evidence.page_number) == (case.document.id, 2)
    assert evidence.excerpt == ""


def test_the_page_text_is_not_returned_even_if_it_is_still_stored(case):
    w = case.world
    with w.uow_factory() as uow:
        uow.documents.mark_file_deleted(case.document.id, FixedClock().now())
        uow.commit()
        assert uow.extractions.list_pages(case.document.id)  # the text is still in the table

    detail = case.get.execute(w.docente, case.document.id)

    assert detail.file_deleted is True
    assert detail.pages == ()


def test_the_listing_still_shows_a_deleted_document(case):
    w = case.world
    case.purge()

    [listed] = case.listing.execute_with_counts(w.docente, w.process.id)

    assert listed.document.id == case.document.id
    assert listed.document.file_deleted_at is not None
    assert listed.activity_count == 1


@pytest.mark.parametrize("closed", [False, True])
def test_reprocessing_and_replacing_a_deleted_document_are_gone(case, closed):
    docs, w = case.docs, case.world
    case.purge()
    if closed:
        case.conclude_process()

    with pytest.raises(Gone) as reprocess:
        docs.reprocess.execute(w.docente, case.document.id)
    with pytest.raises(Gone) as replace:
        docs.replace.execute(
            w.docente, case.document.id, docs.incoming(pdf("novo"), "novo.pdf")
        )

    assert reprocess.value.code == replace.value.code == "ARQUIVO_EXCLUIDO"
    with w.uow_factory() as uow:
        assert uow.jobs.active_for_document(case.document.id) is None


def test_outside_the_access_a_deleted_document_is_still_not_found(case):
    case.purge()

    with pytest.raises(NotFound):
        case.download.execute(case.world.other_docente, case.document.id, inline=False)
    with pytest.raises(NotFound):
        case.get.execute(case.world.other_docente, case.document.id)
    with pytest.raises(NotFound):
        case.download.execute(case.world.docente, uuid.uuid4(), inline=False)
