"""DEL-01, DEL-02, DEL-03, DEL-04, DEL-15 (T87): the conclusion routes."""

import pytest

from app.domain.entities.generated import DocumentKind
from app.domain.entities.user import Role
from tests.integration.api.documents_support import (
    finish_processing,
    pdf,
    stored_files,
    upload_one,
)
from tests.integration.api.generated_support import (
    add_all_ready,
    add_document_row,
    add_ready,
    process_url,
)


def conclusion_url(process) -> str:
    return process_url(process, "conclusion")


def version_of(client, process) -> int:
    return client.get(f"/api/processes/{process['id']}").json()["version"]


def conclude(client, scenario, confirmar=True, **extra):
    body = {"expected_version": version_of(client, scenario.process), "confirmar": confirmar}
    return client.post(
        conclusion_url(scenario.process), json={**body, **extra}, headers=scenario.headers
    )


def start_process(client, scenario) -> None:
    """A process is concluded only from EM_ANDAMENTO; a new one is a RASCUNHO."""
    response = client.post(
        process_url(scenario.process, "status"),
        json={
            "status": "EM_ANDAMENTO",
            "expected_version": version_of(client, scenario.process),
        },
        headers=scenario.headers,
    )
    assert response.status_code == 200, response.text


@pytest.fixture
def stored(client, scenario, uow_factory):
    """A process under way with one input document really stored and already read by the
    executor."""
    start_process(client, scenario)
    document = upload_one(client, scenario.headers, scenario.process, "entrada")
    finish_processing(uow_factory, document)
    scenario.document = document
    return scenario


def test_the_preview_gives_files_bytes_and_whether_each_kind_has_a_ready_version(
    client, stored, uow_factory
):
    before = client.get(conclusion_url(stored.process))
    add_ready(uow_factory, stored.process, stored.user, DocumentKind.TABELA)
    after = client.get(conclusion_url(stored.process)).json()

    assert before.status_code == 200
    assert before.json() == {
        "files": 1,
        "bytes": len(pdf("entrada")),
        "artifacts": {"TABELA": False, "RELATORIO": False, "COMPROVANTE": False},
    }
    assert after["artifacts"] == {"TABELA": True, "RELATORIO": False, "COMPROVANTE": False}


def test_the_preview_counts_a_document_flagged_outside_the_interstice(client, stored, uow_factory):
    add_document_row(
        uow_factory,
        stored.process,
        stored.user,
        status_code="DOCUMENTO_FORA_DO_INTERSTICIO",
        size_bytes=500,
    )

    body = client.get(conclusion_url(stored.process)).json()

    assert (body["files"], body["bytes"]) == (2, len(pdf("entrada")) + 500)


def test_without_the_confirmation_it_is_422_and_nothing_is_removed(
    client, stored, uow_factory, tmp_path
):
    add_all_ready(uow_factory, stored.process, stored.user)

    response = conclude(client, stored, confirmar=False)

    assert response.status_code == 422
    [detail] = response.json()["detail"]
    assert (detail["field"], detail["code"]) == ("geracao", "CONFIRMACAO_OBRIGATORIA")
    assert len(stored_files(tmp_path)) == 1
    assert client.get(f"/api/processes/{stored.process['id']}").json()["status"] != "CONCLUIDO"


def test_a_missing_generated_document_is_422_with_the_kinds_that_are_missing(
    client, stored, uow_factory, tmp_path
):
    add_ready(uow_factory, stored.process, stored.user, DocumentKind.TABELA)

    response = conclude(client, stored)

    assert response.status_code == 422
    [detail] = response.json()["detail"]
    assert detail["code"] == "ARTEFATOS_PENDENTES"
    assert "RELATORIO" in detail["message"] and "COMPROVANTE" in detail["message"]
    assert "TABELA" not in detail["message"]
    assert len(stored_files(tmp_path)) == 1


def test_an_operation_in_progress_is_409_with_the_code(client, scenario, uow_factory, tmp_path):
    start_process(client, scenario)
    upload_one(client, scenario.headers, scenario.process, "lendo")  # its reading is still queued
    add_all_ready(uow_factory, scenario.process, scenario.user)

    response = conclude(client, scenario)

    assert response.status_code == 409
    assert response.json()["code"] == "OPERACAO_EM_ANDAMENTO"
    assert len(stored_files(tmp_path)) == 1


def test_a_stale_process_version_is_409_with_the_code(client, stored, uow_factory):
    add_all_ready(uow_factory, stored.process, stored.user)
    current = version_of(client, stored.process)

    response = client.post(
        conclusion_url(stored.process),
        json={"expected_version": current - 1, "confirmar": True},
        headers=stored.headers,
    )

    assert response.status_code == 409
    assert response.json()["code"] == "VERSAO_DESATUALIZADA"


def test_concluding_removes_the_input_documents_and_answers_with_what_was_freed(
    client, stored, uow_factory, tmp_path
):
    add_all_ready(uow_factory, stored.process, stored.user)

    response = conclude(client, stored, justificativa="Processo entregue")

    assert response.status_code == 200
    assert response.json() == {
        "status": "CONCLUIDO",
        "arquivos_removidos": 1,
        "arquivos_pendentes": 0,
        "bytes_liberados": len(pdf("entrada")),
        "alertas": [],
    }
    assert stored_files(tmp_path) == []
    assert client.get(f"/api/processes/{stored.process['id']}").json()["status"] == "CONCLUIDO"
    assert client.get(f"/api/documents/{stored.document['id']}/file").status_code == 410
    assert client.get(conclusion_url(stored.process)).json()["files"] == 0


def test_repeating_the_conclusion_of_a_concluded_process_changes_nothing(
    client, stored, uow_factory
):
    add_all_ready(uow_factory, stored.process, stored.user)
    conclude(client, stored)

    again = conclude(client, stored)

    assert again.status_code == 200
    assert again.json() == {
        "status": "CONCLUIDO",
        "arquivos_removidos": 0,
        "arquivos_pendentes": 0,
        "bytes_liberados": 0,
        "alertas": [],
    }


def test_a_file_that_cannot_be_removed_leaves_the_process_open_with_the_partial_alert(
    client, stored, uow_factory, monkeypatch, tmp_path
):
    add_all_ready(uow_factory, stored.process, stored.user)
    storage = client.app.state.container.storage
    delete = storage.delete

    def refuse(*args, **kwargs):
        raise OSError("disco somente leitura")

    monkeypatch.setattr(storage, "delete", refuse)
    partial = conclude(client, stored)
    monkeypatch.setattr(storage, "delete", delete)
    finished = conclude(client, stored)

    assert partial.status_code == 200
    body = partial.json()
    assert (body["status"], body["arquivos_removidos"], body["arquivos_pendentes"]) == (
        "EM_ANDAMENTO",
        0,
        1,
    )
    assert [a["code"] for a in body["alertas"]] == ["EXCLUSAO_PARCIAL"]
    assert (finished.json()["status"], finished.json()["arquivos_removidos"]) == ("CONCLUIDO", 1)
    assert stored_files(tmp_path) == []


def test_without_access_to_the_process_both_routes_are_404_and_nothing_is_removed(
    client, stored, uow_factory, act_as, reference, tmp_path
):
    add_all_ready(uow_factory, stored.process, stored.user)
    version = version_of(client, stored.process)
    _, outsider = act_as(
        "fora@ufpa.br", Role.SECRETARIA, unit_ids=frozenset({reference["IFCH"].id})
    )

    assert client.get(conclusion_url(stored.process)).status_code == 404
    denied = client.post(
        conclusion_url(stored.process),
        json={"expected_version": version, "confirmar": True},
        headers=outsider,
    )
    assert denied.status_code == 404
    assert len(stored_files(tmp_path)) == 1


def test_an_unknown_field_in_the_body_is_422(client, stored):
    response = conclude(client, stored, forcar=True)

    assert response.status_code == 422


def test_a_process_that_is_still_a_draft_cannot_be_concluded_and_nothing_is_removed(
    client, scenario, uow_factory, tmp_path
):
    document = upload_one(client, scenario.headers, scenario.process, "rascunho")
    finish_processing(uow_factory, document)
    add_all_ready(uow_factory, scenario.process, scenario.user)

    response = conclude(client, scenario)

    assert response.status_code == 409
    assert len(stored_files(tmp_path)) == 1
