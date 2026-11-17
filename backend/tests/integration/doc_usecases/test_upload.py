"""DOC-01..DOC-07, DOC-12..DOC-14 and the repeated-file edge case: UploadDocuments."""

import hashlib
from datetime import timedelta

import pytest

from app.application.use_cases.documents import DocumentLimits
from app.domain.entities.audit import AuditAction
from app.domain.entities.document import DocumentStatus
from app.domain.entities.process import ProcessStatus
from app.domain.errors import Conflict, NotFound
from app.domain.repositories.ports import JobStatus
from tests.integration.doc_usecases.support import pdf
from tests.support import synthetic_docs as synth


def stored_document(docs, document_id):
    with docs.world.uow_factory() as uow:
        return uow.documents.get(document_id)


def active_job(docs, document_id):
    with docs.world.uow_factory() as uow:
        return uow.jobs.active_for_document(document_id)


def all_documents(docs, process):
    with docs.world.uow_factory() as uow:
        return list(uow.documents.list_for_process(process.id))


# --- independent test of the story: valid + duplicate + swapped extension ---------------------


def test_batch_of_three_gives_201_409_and_422_and_stores_only_the_valid_one(docs, stored_files):
    w = docs.world
    first = docs.incoming(pdf("existente"), "existente.pdf")
    docs.upload.execute(w.docente, w.process.id, [first])
    existing_id = all_documents(docs, w.process)[0].id

    valid = docs.incoming(pdf("valido"), "valido.pdf")
    duplicate = docs.incoming(pdf("existente"), "copia.pdf")
    swapped = docs.incoming(synth.png_with_text(), "falso.pdf")

    results = docs.upload.execute(w.docente, w.process.id, [valid, duplicate, swapped])

    assert [r.status_code for r in results] == [201, 409, 422]
    assert results[0].document.original_name == "valido.pdf"
    assert results[1].existing_document_id == existing_id
    assert (results[2].field, results[2].code) == ("arquivo", "ASSINATURA_DIVERGENTE")
    assert len(all_documents(docs, w.process)) == 2
    assert len(stored_files()) == 2


def test_valid_file_is_stored_with_metadata_and_a_pending_job(docs, stored_files):
    w = docs.world
    content = pdf("metadados", pages=3)

    [result] = docs.upload.execute(
        w.docente, w.process.id, [docs.incoming(content, "Minha Declaração.PDF")]
    )

    document = stored_document(docs, result.document.id)
    assert result.status_code == 201
    assert document.status is DocumentStatus.PENDENTE
    assert document.original_name == "Minha Declaração.PDF"
    assert document.mime == "application/pdf"
    assert document.size_bytes == len(content)
    assert document.sha256 == hashlib.sha256(content).hexdigest()
    assert document.page_count == 3
    assert document.uploaded_by == w.docente.id
    assert document.uploaded_at == docs.clock.now()
    assert document.process_id == w.process.id
    assert document.internal_name != document.original_name
    assert document.internal_name.endswith(".pdf")
    [path] = stored_files()
    assert path == docs.storage.path(w.process.id, document.internal_name)
    assert path.read_bytes() == content
    job = active_job(docs, document.id)
    assert job.status is JobStatus.PENDENTE


@pytest.mark.parametrize(
    ("content", "name", "mime", "kind_mime", "pages"),
    [
        (synth.jpg_with_text(), "foto.jpg", "image/jpeg", "image/jpeg", 1),
        (synth.jpg_with_text(), "foto.jpeg", None, "image/jpeg", 1),
        (synth.png_with_text(), "imagem.png", "image/png", "image/png", 1),
    ],
)
def test_images_are_accepted_with_one_page_and_canonical_mime(
    docs, content, name, mime, kind_mime, pages
):
    w = docs.world

    [result] = docs.upload.execute(w.docente, w.process.id, [docs.incoming(content, name, mime)])

    assert result.status_code == 201
    assert result.document.mime == kind_mime
    assert result.document.page_count == pages


# --- repeated file in the same request ---------------------------------------------------------


def test_same_file_twice_in_one_request_stores_the_first_and_gives_409_to_the_second(
    docs, stored_files
):
    w = docs.world
    content = pdf("repetido")

    first, second = docs.upload.execute(
        w.docente,
        w.process.id,
        [docs.incoming(content, "a.pdf"), docs.incoming(content, "b.pdf")],
    )

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.existing_document_id == first.document.id
    assert len(all_documents(docs, w.process)) == 1
    assert len(stored_files()) == 1


def test_same_file_is_allowed_in_a_different_process(docs, add_process):
    w = docs.world
    other = add_process()
    content = pdf("dois-processos")

    [first] = docs.upload.execute(w.docente, w.process.id, [docs.incoming(content)])
    [second] = docs.upload.execute(w.docente, other.id, [docs.incoming(content)])

    assert (first.status_code, second.status_code) == (201, 201)
    assert first.document.id != second.document.id


# --- rejections: 422 on `arquivo`, nothing stored ----------------------------------------------


@pytest.mark.parametrize(
    ("content", "name", "mime", "code"),
    [
        (b"MZ not a document", "programa.exe", None, "EXTENSAO_INVALIDA"),
        (pdf("x"), "relatorio.docx", None, "EXTENSAO_INVALIDA"),
        (synth.png_with_text(), "trocado.pdf", "application/pdf", "ASSINATURA_DIVERGENTE"),
        (pdf("mime"), "mime.pdf", "image/png", "MIME_DIVERGENTE"),
        (synth.pdf_with_javascript(), "js.pdf", "application/pdf", "ARQUIVO_INVALIDO"),
        (synth.pdf_encrypted(), "senha.pdf", "application/pdf", "ARQUIVO_INVALIDO"),
        (synth.pdf_with_embedded_file(), "anexo.pdf", "application/pdf", "ARQUIVO_INVALIDO"),
        (b"%PDF-1.4 quebrado", "quebrado.pdf", "application/pdf", "ARQUIVO_INVALIDO"),
        (synth.png_huge(), "gigante.png", "image/png", "IMAGEM_GRANDE"),
    ],
)
def test_rejected_files_give_422_on_arquivo_and_are_not_stored(
    docs, stored_files, content, name, mime, code
):
    w = docs.world

    [result] = docs.upload.execute(w.docente, w.process.id, [docs.incoming(content, name, mime)])

    assert result.status_code == 422
    assert result.field == "arquivo"
    assert result.code == code
    assert result.document is None
    assert all_documents(docs, w.process) == []
    assert stored_files() == []


def test_file_above_the_size_limit_gives_422_on_arquivo(docs):
    w = docs.world
    content = pdf("grande", pages=3)
    upload = docs.upload_with(DocumentLimits(max_file_bytes=len(content) - 1))

    [result] = upload.execute(w.docente, w.process.id, [docs.incoming(content)])

    assert (result.status_code, result.field, result.code) == (422, "arquivo", "ARQUIVO_GRANDE")


def test_pdf_above_the_page_limit_gives_422_on_arquivo(docs):
    w = docs.world
    upload = docs.upload_with(DocumentLimits(max_pages=2))

    [result] = upload.execute(w.docente, w.process.id, [docs.incoming(pdf("paginas", pages=3))])

    assert (result.status_code, result.field, result.code) == (422, "arquivo", "PAGINAS_EXCEDIDAS")


def test_a_rejected_file_does_not_stop_the_next_ones(docs):
    w = docs.world

    bad, good = docs.upload.execute(
        w.docente,
        w.process.id,
        [docs.incoming(b"MZ", "x.exe"), docs.incoming(pdf("depois"), "depois.pdf")],
    )

    assert (bad.status_code, good.status_code) == (422, 201)


def test_original_name_with_path_parts_is_display_text_and_never_a_path(docs, stored_files):
    w = docs.world
    long_name = "a" * 300 + ".pdf"

    traversal, long = docs.upload.execute(
        w.docente,
        w.process.id,
        [
            docs.incoming(pdf("t1"), "../../etc/passwd.pdf"),
            docs.incoming(pdf("t2"), long_name),
        ],
    )

    assert traversal.document.original_name == "passwd.pdf"
    assert len(long.document.original_name) <= 255
    assert long.document.original_name.endswith(".pdf")
    for document in (traversal.document, long.document):
        assert ".." not in document.internal_name and "/" not in document.internal_name
    for path in stored_files():
        assert path.is_relative_to(docs.storage_root)
        assert path.parent.name == str(w.process.id)


# --- limits: 200 documents per process, 60 uploads per minute ----------------------------------


def test_process_with_200_documents_refuses_the_next_with_422_on_limite(docs, stored_files):
    w = docs.world
    docs.add_documents(w.process, w.admin, 200, uploaded_at=docs.clock.now() - timedelta(days=1))

    [result] = docs.upload.execute(w.docente, w.process.id, [docs.incoming(pdf("201"))])

    assert result.status_code == 422
    assert result.field == "limite"
    assert result.document is None
    assert stored_files() == []


def test_process_with_199_documents_accepts_the_200th(docs):
    w = docs.world
    docs.add_documents(w.process, w.admin, 199, uploaded_at=docs.clock.now() - timedelta(days=1))

    [result] = docs.upload.execute(w.docente, w.process.id, [docs.incoming(pdf("200"))])

    assert result.status_code == 201


def test_61st_upload_in_the_minute_gives_429_and_the_60th_is_accepted(docs):
    w = docs.world
    docs.add_documents(w.process, w.docente, 59)

    sixtieth, sixty_first = docs.upload.execute(
        w.docente, w.process.id, [docs.incoming(pdf("60")), docs.incoming(pdf("61"))]
    )

    assert sixtieth.status_code == 201
    assert sixty_first.status_code == 429
    assert sixty_first.document is None
    assert len(all_documents(docs, w.process)) == 60


def test_excess_of_one_request_counts_the_files_of_the_same_request(docs):
    w = docs.world
    docs.add_documents(w.process, w.docente, 58)

    results = docs.upload.execute(
        w.docente, w.process.id, [docs.incoming(pdf(f"lote-{n}")) for n in range(4)]
    )

    assert [r.status_code for r in results] == [201, 201, 429, 429]


def test_uploads_older_than_a_minute_and_of_other_users_do_not_count(docs):
    w = docs.world
    two_minutes_ago = docs.clock.now() - timedelta(minutes=2)
    docs.add_documents(w.process, w.docente, 60, uploaded_at=two_minutes_ago)
    docs.add_documents(w.process, w.admin, 60)

    [result] = docs.upload.execute(w.docente, w.process.id, [docs.incoming(pdf("livre"))])

    assert result.status_code == 201


# --- process state and access -----------------------------------------------------------------


@pytest.mark.parametrize("status", [ProcessStatus.CONCLUIDO, ProcessStatus.ARQUIVADO])
def test_closed_process_refuses_the_whole_request_with_conflict(docs, add_process, status):
    w = docs.world
    closed = add_process(status=status)

    with pytest.raises(Conflict):
        docs.upload.execute(w.docente, closed.id, [docs.incoming(pdf("fechado"))])

    assert all_documents(docs, closed) == []


def test_users_without_access_get_not_found_and_nothing_is_stored(docs, stored_files):
    w = docs.world
    for actor in (w.other_docente, w.other_secretaria):
        with pytest.raises(NotFound):
            docs.upload.execute(actor, w.process.id, [docs.incoming(pdf("sem-acesso"))])
    assert all_documents(docs, w.process) == []
    assert stored_files() == []


def test_unknown_process_is_not_found(docs):
    import uuid

    with pytest.raises(NotFound):
        docs.upload.execute(docs.world.admin, uuid.uuid4(), [docs.incoming(pdf("x"))])


@pytest.mark.parametrize("actor_name", ["admin", "docente", "secretaria"])
def test_admin_owner_and_unit_secretaria_may_upload(docs, actor_name):
    w = docs.world

    [result] = docs.upload.execute(
        getattr(w, actor_name), w.process.id, [docs.incoming(pdf(actor_name))]
    )

    assert result.status_code == 201
    assert result.document.uploaded_by == getattr(w, actor_name).id


# --- audit -------------------------------------------------------------------------------------


def test_upload_audit_has_user_time_document_and_operation_without_content(docs):
    w = docs.world
    content = synth.pdf_with_text(["Texto secreto do documento ficticio"])

    [result] = docs.upload.execute(
        w.docente, w.process.id, [docs.incoming(content, "banca.pdf")]
    )

    with w.uow_factory() as uow:
        [event] = uow.audit.list_for("document", str(result.document.id))
    assert event.user_id == w.docente.id
    assert event.occurred_at == docs.clock.now()
    assert event.entity_id == str(result.document.id)
    assert event.action is AuditAction.CREATE
    assert set(event.changes) == {"operation", "original_name", "sha256", "status"}
    assert event.changes["operation"]["after"] == "UPLOAD"
    assert event.changes["original_name"]["after"] == "banca.pdf"
    assert event.changes["sha256"]["after"] == hashlib.sha256(content).hexdigest()
    assert event.changes["status"]["after"] == "PENDENTE"
    assert "secreto" not in str(event.changes)


def test_rejected_and_duplicate_files_write_no_audit(docs):
    w = docs.world
    content = pdf("auditoria")
    docs.upload.execute(w.docente, w.process.id, [docs.incoming(content)])

    docs.upload.execute(
        w.docente,
        w.process.id,
        [docs.incoming(content), docs.incoming(b"MZ", "x.exe")],
    )

    with w.uow_factory() as uow:
        [document] = uow.documents.list_for_process(w.process.id)
        assert len(uow.audit.list_for("document", str(document.id))) == 1


# --- atomicity ---------------------------------------------------------------------------------


def test_failure_while_saving_the_job_leaves_no_document_and_no_stored_file(docs, stored_files):
    w = docs.world

    class FailingJobs:
        def add(self, job):
            raise RuntimeError("falha simulada")

    class JobsFailUnitOfWork:
        """The real unit of work, with a job repository that fails on add."""

        def __init__(self, inner):
            self._inner = inner

        def __enter__(self):
            self._inner.__enter__()
            self._inner.jobs = FailingJobs()
            return self._inner

        def __exit__(self, *exc):
            return self._inner.__exit__(*exc)

    def factory():
        return JobsFailUnitOfWork(w.uow_factory())

    upload = docs.upload_with(uow_factory=factory)

    with pytest.raises(RuntimeError):
        upload.execute(w.docente, w.process.id, [docs.incoming(pdf("falha"))])

    assert all_documents(docs, w.process) == []
    assert stored_files() == []
