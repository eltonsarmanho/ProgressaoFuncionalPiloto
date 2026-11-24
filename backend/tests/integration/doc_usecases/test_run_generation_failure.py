"""VER-05, CMP-09, CMP-10, VER-07: a generation that fails leaves no file and a closed row."""

import dataclasses
import json
import logging

from app.domain.entities.audit import AuditAction
from app.domain.entities.generated import DocumentKind, GenerationCode, GenerationState
from app.infrastructure.documents.document_writer import FileDocumentWriter
from app.infrastructure.storage.generated_storage import LocalGeneratedStorage
from tests.integration.doc_usecases.generation_support import add_activity, link, store_original
from tests.support import synthetic_docs as synth

PERSON = "Maria Aparecida Souza"
SECRET = "segredo-da-excecao-123"


def stored_files(gen):
    root = gen.docs.storage_root / "generated"
    return sorted(p.name for p in root.rglob("*") if p.is_file())


def request_and_run(gen, kind, **overrides):
    requested = gen.request().execute(gen.world.admin, gen.world.process.id, kind)
    assert gen.run(**overrides).run_next() is True
    with gen.world.uow_factory() as uow:
        return uow.generations.get(requested.id)


def comprovante_with_a_page(gen):
    world = gen.world
    activity = add_activity(world, title=f"Orientação de {PERSON}")
    document = store_original(
        gen,
        world.process,
        synth.pdf_with_text(["pagina um", "pagina dois"]),
        original_name=f"{PERSON} declaracao.pdf",
    )
    link(world, activity, document, 1)
    return document


def test_an_original_deleted_after_the_request_fails_with_a_fixed_message_and_no_file(gen):
    document = comprovante_with_a_page(gen)
    requested = gen.request().execute(
        gen.world.admin, gen.world.process.id, DocumentKind.COMPROVANTE
    )
    gen.originals.delete(gen.world.process.id, document.internal_name)

    assert gen.run().run_next() is True

    with gen.world.uow_factory() as uow:
        failed = uow.generations.get(requested.id)
    assert failed.state is GenerationState.FALHOU
    assert failed.error_code is GenerationCode.ORIGINAL_INDISPONIVEL
    assert failed.version_number is None and failed.files == ()
    assert PERSON not in failed.error_message and failed.error_message
    assert stored_files(gen) == []


def test_a_valid_activity_without_category_after_the_request_fails_with_its_code(gen):
    # SEG-05: the request went through; the worker finds the activity and says so, not ERRO_INTERNO
    add_activity(gen.world, title="Orientação com categoria")
    requested = gen.request().execute(gen.world.admin, gen.world.process.id, DocumentKind.TABELA)
    add_activity(gen.world, title="Sem categoria", group_number=None, item_number=None)

    assert gen.run().run_next() is True

    with gen.world.uow_factory() as uow:
        failed = uow.generations.get(requested.id)
    assert failed.state is GenerationState.FALHOU
    assert failed.error_code is GenerationCode.ATIVIDADE_SEM_CATEGORIA
    assert failed.error_message == (
        "Há atividades sem categoria na Etapa 3. Escolha a categoria de cada uma."
    )
    assert failed.version_number is None and failed.files == ()
    assert stored_files(gen) == []


class FailingWriter:
    """Writes the first format and breaks on the second."""

    def __init__(self) -> None:
        self._real = FileDocumentWriter()
        self.calls = 0

    def write_table(self, model, fmt, target):
        self.calls += 1
        if self.calls == 2:
            raise RuntimeError(SECRET)
        self._real.write_table(model, fmt, target)


def test_a_failure_in_the_second_format_removes_the_first_and_spends_no_version(gen):
    add_activity(gen.world, title=f"Orientação de {PERSON}")

    failed = request_and_run(gen, DocumentKind.TABELA, writer=FailingWriter())

    assert failed.state is GenerationState.FALHOU
    assert failed.error_code is GenerationCode.ERRO_INTERNO
    assert SECRET not in failed.error_message
    assert stored_files(gen) == []
    retried = request_and_run(gen, DocumentKind.TABELA)
    assert (retried.state, retried.version_number) == (GenerationState.PRONTO, 1)


class CommitFailingStorage(LocalGeneratedStorage):
    """Renames the first file and breaks on the second."""

    def __init__(self, root) -> None:
        super().__init__(root)
        self.commits = 0

    def commit(self, process_id, temp, extension):
        self.commits += 1
        if self.commits == 2:
            raise OSError(SECRET)
        return super().commit(process_id, temp, extension)


def test_a_file_already_renamed_is_deleted_when_a_later_step_fails(gen):
    add_activity(gen.world)
    storage = CommitFailingStorage(gen.docs.storage_root)

    failed = request_and_run(gen, DocumentKind.TABELA, storage=storage)

    assert storage.commits == 2
    assert failed.state is GenerationState.FALHOU
    assert failed.error_code is GenerationCode.ERRO_INTERNO
    assert stored_files(gen) == []


def test_the_failure_is_audited_with_the_code_and_no_content(gen):
    document = comprovante_with_a_page(gen)
    requested = gen.request().execute(
        gen.world.admin, gen.world.process.id, DocumentKind.COMPROVANTE
    )
    gen.originals.delete(gen.world.process.id, document.internal_name)
    gen.run().run_next()

    with gen.world.uow_factory() as uow:
        events = uow.audit.list_for("generated_document", str(requested.id))
    [status] = [e for e in events if e.action is AuditAction.STATUS]
    assert status.changes["state"] == {"before": "GERANDO", "after": "FALHOU"}
    assert status.changes["error_code"] == {"before": None, "after": "ORIGINAL_INDISPONIVEL"}
    assert PERSON not in json.dumps(status.changes)


def test_the_log_of_a_failed_generation_has_no_text_of_the_documents(gen, caplog):
    add_activity(gen.world, title=f"Orientação de {PERSON}")

    with caplog.at_level(logging.DEBUG):
        request_and_run(gen, DocumentKind.TABELA, writer=FailingWriter())

    assert "ERRO_INTERNO" in caplog.text
    assert PERSON not in caplog.text and SECRET not in caplog.text


class Invented:
    """A kind of document that no code knows."""

    value = "INVENTADO"


class _InventedKindGenerations:
    """The generation repository, but every row it reads says the invented kind."""

    def __init__(self, real) -> None:
        self._real = real

    def get(self, generation_id):
        row = self._real.get(generation_id)
        return None if row is None else dataclasses.replace(row, kind=Invented())

    def __getattr__(self, name):
        return getattr(self._real, name)


class _InventedKindUow:
    def __init__(self, real) -> None:
        self._real = real

    def __enter__(self):
        self._real.__enter__()
        return self

    def __exit__(self, *exc):
        return self._real.__exit__(*exc)

    @property
    def generations(self):
        return _InventedKindGenerations(self._real.generations)

    def __getattr__(self, name):
        return getattr(self._real, name)


def test_a_kind_no_code_knows_fails_with_an_internal_error_and_never_becomes_a_tabela(gen, caplog):
    add_activity(gen.world)
    requested = gen.request().execute(gen.world.admin, gen.world.process.id, DocumentKind.TABELA)
    factory = gen.world.uow_factory

    with caplog.at_level(logging.DEBUG):
        assert gen.run(uow_factory=lambda: _InventedKindUow(factory())).run_next() is True

    with factory() as uow:
        failed = uow.generations.get(requested.id)
    assert failed.state is GenerationState.FALHOU
    assert failed.error_code is GenerationCode.ERRO_INTERNO
    assert failed.version_number is None and failed.files == ()
    assert stored_files(gen) == []
    assert "error_type=ValueError" in caplog.text
    assert "unknown kind" not in caplog.text  # the log carries the type of the error, not its text
