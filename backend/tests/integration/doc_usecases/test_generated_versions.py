"""VER-03, VER-06, VER-09, DEL-13: listing, reading and downloading the stored versions."""

import dataclasses
import uuid

import pytest

from app.application.use_cases.generated_documents import (
    DownloadGeneratedFile,
    GetGeneratedDocument,
    ListGeneratedDocuments,
)
from app.domain.entities.audit import AuditAction
from app.domain.entities.generated import (
    DocumentFormat,
    DocumentKind,
    GenerationCode,
    GenerationState,
)
from app.domain.entities.process import ProcessStatus
from app.domain.errors import NotFound
from tests.integration.doc_usecases.generation_support import add_activity
from tests.integration.doc_usecases.test_run_generation_table import file_of, generate

DOCX_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def use_cases(gen):
    world = gen.world
    args = (world.uow_factory, world.audit, world.policy)
    return (
        ListGeneratedDocuments(*args),
        GetGeneratedDocument(*args),
        DownloadGeneratedFile(*args, gen.generated),
    )


def two_tables_and_a_running_report(gen):
    """Tabela v1 and v2 (a minute apart) and a Relatório still GERANDO."""
    add_activity(gen.world)
    first = generate(gen)
    gen.clock.advance(minutes=1)
    second = generate(gen)
    gen.clock.advance(minutes=1)
    running = gen.request().execute(gen.world.admin, gen.world.process.id, DocumentKind.RELATORIO)
    return first, second, running


def test_the_list_has_the_running_one_first_then_the_newest_with_the_data_of_each(gen):
    first, second, running = two_tables_and_a_running_report(gen)
    listing, _, _ = use_cases(gen)

    found = listing.execute(gen.world.admin, gen.world.process.id)

    assert [g.id for g in found] == [running.id, second.id, first.id]
    assert found[0].state is GenerationState.GERANDO
    assert [(g.state, g.version_number) for g in found[1:]] == [
        (GenerationState.PRONTO, 2),
        (GenerationState.PRONTO, 1),
    ]
    assert found[1].alerts == second.alerts
    assert [(f.format, f.size_bytes) for f in found[2].files] == [
        (f.format, f.size_bytes) for f in first.files
    ]
    assert all(f.size_bytes > 0 for f in found[1].files)


def test_the_list_can_be_filtered_by_kind(gen):
    first, second, _ = two_tables_and_a_running_report(gen)
    listing, _, _ = use_cases(gen)

    found = listing.execute(gen.world.admin, gen.world.process.id, DocumentKind.TABELA)

    assert [g.id for g in found] == [second.id, first.id]


def test_a_version_is_read_with_its_files_and_snapshot(gen):
    first, _, _ = two_tables_and_a_running_report(gen)
    _, get, _ = use_cases(gen)

    found = get.execute(gen.world.admin, first.id)

    assert found == first
    assert found.snapshot["total"] == first.snapshot["total"]


def test_version_1_downloaded_after_the_process_changed_is_the_stored_file_byte_for_byte(gen):
    world = gen.world
    add_activity(world, title="Atividade original")
    first = generate(gen)
    stored = file_of(gen, first, DocumentFormat.PDF)[1].read_bytes()
    add_activity(world, title="Atividade nova que muda a tabela", item_number=8)
    generate(gen)
    _, _, download = use_cases(gen)
    with world.uow_factory() as uow:
        before = len(uow.generations.list_for_process(world.process.id))

    received = download.execute(world.admin, first.id, DocumentFormat.PDF)

    assert received.path.read_bytes() == stored
    with world.uow_factory() as uow:
        assert len(uow.generations.list_for_process(world.process.id)) == before


def test_the_download_has_the_server_made_name_the_type_and_the_hash_for_the_etag(gen):
    add_activity(gen.world)
    done = generate(gen)
    _, _, download = use_cases(gen)

    pdf = download.execute(gen.world.admin, done.id, DocumentFormat.PDF)
    docx = download.execute(gen.world.admin, done.id, DocumentFormat.DOCX)

    assert pdf.filename == "Tabela_de_Pontuacao_2022-2024_v1.pdf"
    assert docx.filename == "Tabela_de_Pontuacao_2022-2024_v1.docx"
    assert (pdf.content_type, docx.content_type) == ("application/pdf", DOCX_TYPE)
    assert pdf.sha256 == file_of(gen, done, DocumentFormat.PDF)[0].sha256


def test_a_download_is_audited_with_the_operation_and_the_format_and_no_content(gen):
    add_activity(gen.world)
    done = generate(gen)
    _, _, download = use_cases(gen)

    download.execute(gen.world.docente, done.id, DocumentFormat.DOCX)

    with gen.world.uow_factory() as uow:
        events = [
            e
            for e in uow.audit.list_for("generated_document", str(done.id))
            if e.action is AuditAction.UPDATE
        ]
    [event] = events
    assert event.user_id == gen.world.docente.id
    assert event.changes == {
        "operation": {"before": None, "after": "DOWNLOAD"},
        "format": {"before": None, "after": "DOCX"},
    }


def test_a_row_that_is_not_ready_or_a_missing_file_or_a_missing_format_is_not_found(gen):
    world = gen.world
    add_activity(world)
    running = gen.request().execute(world.admin, world.process.id, DocumentKind.TABELA)
    _, _, download = use_cases(gen)
    with pytest.raises(NotFound):
        download.execute(world.admin, running.id, DocumentFormat.PDF)

    with world.uow_factory() as uow:
        uow.generations.finish_failed(
            running.id, gen.clock.now(), GenerationCode.ERRO_INTERNO, "Erro"
        )
        uow.commit()
    with pytest.raises(NotFound):
        download.execute(world.admin, running.id, DocumentFormat.PDF)

    done = generate(gen)
    file_of(gen, done, DocumentFormat.PDF)[1].unlink()
    with pytest.raises(NotFound):
        download.execute(world.admin, done.id, DocumentFormat.PDF)

    comprovante = generate(gen, DocumentKind.COMPROVANTE)
    with pytest.raises(NotFound):
        download.execute(world.admin, comprovante.id, DocumentFormat.DOCX)


def test_another_professor_gets_not_found_for_list_read_and_download(gen):
    add_activity(gen.world)
    done = generate(gen)
    listing, get, download = use_cases(gen)
    stranger = gen.world.other_docente

    with pytest.raises(NotFound):
        listing.execute(stranger, gen.world.process.id)
    with pytest.raises(NotFound):
        get.execute(stranger, done.id)
    with pytest.raises(NotFound):
        download.execute(stranger, done.id, DocumentFormat.PDF)


def test_an_unknown_version_is_not_found(gen):
    _, get, download = use_cases(gen)

    with pytest.raises(NotFound):
        get.execute(gen.world.admin, uuid.uuid4())
    with pytest.raises(NotFound):
        download.execute(gen.world.admin, uuid.uuid4(), DocumentFormat.PDF)


def test_in_a_concluded_process_the_versions_are_still_listed_and_downloadable(gen):
    world = gen.world
    add_activity(world)
    done = generate(gen)
    with world.uow_factory() as uow:
        current = uow.processes.get(world.process.id)
        uow.processes.update(
            dataclasses.replace(current, status=ProcessStatus.CONCLUIDO), current.version
        )
        uow.commit()
    listing, _, download = use_cases(gen)

    assert [g.id for g in listing.execute(world.admin, world.process.id)] == [done.id]
    assert download.execute(world.admin, done.id, DocumentFormat.PDF).path.is_file()
