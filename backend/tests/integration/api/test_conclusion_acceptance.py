"""DEL-05 to DEL-09, DEL-11 to DEL-13 (T93): concluding a synthetic process through the API, with
the three generated documents really generated, one input document outside the interstice and
one removal that fails the first time.

The process is EM_ANDAMENTO with three input documents (two linked to the activity, one flagged
as outside the interstice) and a ready version of the Tabela, the Relatório and the Comprovante.
"""

import hashlib
import uuid
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.domain.entities.document import DocumentStatus
from app.domain.entities.generated import DocumentKind
from app.domain.repositories.ports import JobStatus
from tests.integration.api.documents_support import seed_run, upload
from tests.integration.api.generated_support import ask, file_url, generate
from tests.integration.api.test_conclusion_api import (
    conclude,
    conclusion_url,
    start_process,
)
from tests.support import synthetic_docs as synth

OUTSIDE = "DOCUMENTO_FORA_DO_INTERSTICIO"


def tree(root: Path) -> dict[str, str]:
    """Every file under `root` with its SHA-256, by relative path."""
    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def put_document(client, uow_factory, scenario, name, outside=False) -> dict:
    """An uploaded two-page PDF, read by the executor (two pages of text), flagged when it fell
    outside the interstice."""
    content = synth.pdf_with_text([f"{name} pagina 1", f"{name} pagina 2"])
    response = upload(client, scenario.headers, scenario.process, (f"{name}.pdf", content))
    assert response.status_code == 201, response.text
    [result] = response.json()
    document = result["document"]
    with uow_factory() as uow:
        row = uow.documents.get(uuid.UUID(document["id"]))
        job = uow.jobs.active_for_document(row.id)
        uow.jobs.finish(job.id, JobStatus.CONCLUIDA, datetime(2026, 11, 16, 9, 5, tzinfo=UTC))
        uow.documents.update(
            replace(
                row, status=DocumentStatus.PROCESSADO, status_code=OUTSIDE if outside else None
            ),
            row.version,
        )
        uow.commit()
    seed_run(uow_factory, row, texts=(f"{name} texto 1", f"{name} texto 2"), warnings=())
    return document


@pytest.fixture
def done(client, scenario, uow_factory, tmp_path):
    """A process under way, three input documents and the three documents generated."""
    start_process(client, scenario)
    first = put_document(client, uow_factory, scenario, "Alfa")
    second = put_document(client, uow_factory, scenario, "Beta")
    third = put_document(client, uow_factory, scenario, "Gama", outside=True)
    for document in (first, second):
        link = client.post(
            f"/api/activities/{scenario.activity['id']}/evidences",
            json={"document_id": document["id"], "page": 1},
            headers=scenario.headers,
        )
        assert link.status_code == 201, link.text
    scenario.documents = [first, second, third]
    scenario.versions = [
        generate(client, scenario.headers, scenario.process, kind.value) for kind in DocumentKind
    ]
    storage = tmp_path / "storage"
    scenario.uploads = storage / "uploads" / scenario.process["id"]
    scenario.generated = storage / "generated"
    scenario.stored_before = tree(scenario.uploads)
    scenario.generated_before = tree(scenario.generated)
    scenario.size_before = sum(p.stat().st_size for p in scenario.uploads.iterdir())
    return scenario


def downloaded(client, versions) -> dict[tuple[str, str], bytes]:
    return {
        (row["id"], f["format"]): client.get(file_url(row, f["format"].lower())).content
        for row in versions
        for f in row["files"]
    }


def test_concluding_removes_every_input_file_keeps_the_generated_ones_and_frees_what_it_said(
    client, done
):
    assert len(done.stored_before) == 3
    preview = client.get(conclusion_url(done.process)).json()
    assert (preview["files"], preview["bytes"]) == (3, done.size_before)
    assert preview["artifacts"] == {"TABELA": True, "RELATORIO": True, "COMPROVANTE": True}

    response = conclude(client, done)

    assert response.status_code == 200, response.text
    assert response.json() == {
        "status": "CONCLUIDO",
        "arquivos_removidos": 3,
        "arquivos_pendentes": 0,
        "bytes_liberados": done.size_before,
        "alertas": [],
    }
    assert [p for p in done.uploads.rglob("*") if p.is_file()] == []
    assert tree(done.generated) == done.generated_before
    assert client.get(f"/api/processes/{done.process['id']}").json()["status"] == "CONCLUIDO"


def test_the_deleted_documents_keep_their_metadata_the_comprovante_is_refused_and_a_page_is_410(
    client, done
):
    conclude(client, done)

    refused = ask(client, done.headers, done.process, "COMPROVANTE")

    assert refused.status_code == 422
    [detail] = refused.json()["detail"]
    assert (detail["field"], detail["code"]) == ("geracao", "ORIGINAIS_EXCLUIDOS")
    for document in done.documents:
        view = client.get(f"/api/documents/{document['id']}/file")
        assert view.status_code == 410
        [error] = view.json()["detail"]
        assert (error["field"], error["code"]) == ("arquivo", "ARQUIVO_EXCLUIDO")
        detail = client.get(f"/api/documents/{document['id']}").json()
        assert detail["arquivo_excluido"] is True
        assert detail["original_name"] == document["original_name"]
        assert (detail["page_count"], detail["pages"]) == (document["page_count"], [])
    outside = client.get(f"/api/documents/{done.documents[2]['id']}").json()
    assert outside["status_code"] == OUTSIDE and outside["arquivo_excluido"] is True


def test_after_the_conclusion_tabela_and_relatorio_generate_again_and_all_versions_download(
    client, done
):
    before = downloaded(client, done.versions)
    conclude(client, done)

    table = generate(client, done.headers, done.process, "TABELA")
    report = generate(client, done.headers, done.process, "RELATORIO")

    assert (table["version_number"], report["version_number"]) == (2, 2)
    assert downloaded(client, done.versions) == before  # byte for byte
    assert all(content.startswith((b"%PDF", b"PK")) for content in before.values())
    assert client.get(file_url(table, "pdf")).status_code == 200


def test_a_locked_file_leaves_the_process_open_with_the_partial_alert_and_the_second_try_ends_it(
    client, done, monkeypatch
):
    storage = client.app.state.container.storage
    delete = storage.delete
    locked = done.documents[1]

    def delete_unless_locked(process_id, internal_name):
        with client.app.state.container.uow_factory() as uow:
            row = uow.documents.get(uuid.UUID(locked["id"]))
        if internal_name == row.internal_name:
            raise OSError("arquivo travado")
        delete(process_id, internal_name)

    monkeypatch.setattr(storage, "delete", delete_unless_locked)
    partial = conclude(client, done)
    monkeypatch.setattr(storage, "delete", delete)
    left = tree(done.uploads)
    process_after_first = client.get(f"/api/processes/{done.process['id']}").json()["status"]
    second = conclude(client, done)

    assert partial.status_code == 200
    body = partial.json()
    assert (body["status"], body["arquivos_removidos"], body["arquivos_pendentes"]) == (
        "EM_ANDAMENTO",
        2,
        1,
    )
    assert [a["code"] for a in body["alertas"]] == ["EXCLUSAO_PARCIAL"]
    assert process_after_first == "EM_ANDAMENTO" and len(left) == 1
    assert (second.json()["status"], second.json()["arquivos_removidos"]) == ("CONCLUIDO", 1)
    assert body["bytes_liberados"] + second.json()["bytes_liberados"] == done.size_before
    assert [p for p in done.uploads.rglob("*") if p.is_file()] == []
    assert tree(done.generated) == done.generated_before
