"""TAB-01, TAB-07, TAB-08, VER-03, VER-04, VER-06, DEL-13 (T83): the generation and download
routes."""

import uuid

import pytest

from app.domain.entities.user import Role
from tests.integration.api.generated_support import (
    ask,
    choose_table,
    file_url,
    generate,
    generations_url,
    link_deleted_original,
    run_executor,
    sha256,
)
from tests.support.process_status import conclude_for_test

DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
ROW_KEYS = {
    "id", "process_id", "kind", "state", "version_number", "requested_at", "started_at",
    "finished_at", "error_code", "error_message", "alerts", "files",
    "table_version_id",  # GI-11
}  # fmt: skip


def test_asking_answers_202_with_the_row_waiting_and_no_number_yet(client, scenario):
    response = ask(client, scenario.headers, scenario.process, "TABELA")

    assert response.status_code == 202
    body = response.json()
    assert set(body) == ROW_KEYS
    assert (body["kind"], body["state"], body["version_number"]) == ("TABELA", "GERANDO", None)
    assert (body["files"], body["process_id"]) == ([], scenario.process["id"])


def test_a_process_without_a_chosen_table_is_refused_with_the_code(
    client, admin, process, scoring_tables
):
    response = ask(client, admin[1], process)

    assert response.status_code == 422
    [detail] = response.json()["detail"]
    assert (detail["field"], detail["code"]) == ("geracao", "TABELA_NAO_ESCOLHIDA")
    assert detail["message"]


def test_a_process_without_a_validated_activity_is_refused_with_the_code(
    client, admin, process, scoring_tables
):
    choose_table(client, admin[1], process, scoring_tables["OFICIAL"])

    response = ask(client, admin[1], process)

    assert response.status_code == 422
    [detail] = response.json()["detail"]
    assert (detail["field"], detail["code"]) == ("geracao", "SEM_ATIVIDADES_VALIDADAS")
    assert detail["message"]


def test_a_second_request_of_a_kind_while_one_runs_is_409_and_another_kind_is_not(client, scenario):
    assert ask(client, scenario.headers, scenario.process, "TABELA").status_code == 202

    second = ask(client, scenario.headers, scenario.process, "TABELA")
    other = ask(client, scenario.headers, scenario.process, "RELATORIO")

    assert second.status_code == 409
    assert second.json()["code"] == "GERACAO_EM_ANDAMENTO"
    assert other.status_code == 202


def test_an_unknown_kind_or_field_in_the_request_is_422(client, scenario):
    wrong_kind = ask(client, scenario.headers, scenario.process, "PARECER")
    extra = client.post(
        generations_url(scenario.process),
        json={"kind": "TABELA", "justificativa": "x"},
        headers=scenario.headers,
    )

    assert wrong_kind.status_code == 422
    assert extra.status_code == 422


def test_without_a_session_or_the_csrf_token_nothing_is_asked(client, scenario):
    no_token = client.post(generations_url(scenario.process), json={"kind": "TABELA"})
    client.cookies.clear()
    no_session = client.post(
        generations_url(scenario.process), json={"kind": "TABELA"}, headers=scenario.headers
    )
    listing = client.get(generations_url(scenario.process))

    assert no_token.status_code == 403
    assert no_session.status_code == 401
    assert listing.status_code == 401


def test_the_list_puts_the_running_row_first_and_shows_the_ready_versions_with_their_files(
    client, scenario
):
    ready = generate(client, scenario.headers, scenario.process, "TABELA")
    assert ask(client, scenario.headers, scenario.process, "RELATORIO").status_code == 202

    rows = client.get(generations_url(scenario.process)).json()

    assert [(r["kind"], r["state"]) for r in rows] == [
        ("RELATORIO", "GERANDO"),
        ("TABELA", "PRONTO"),
    ]
    assert rows[1]["id"] == ready["id"] and rows[1]["version_number"] == 1
    assert [(f["format"], f["size_bytes"] > 0) for f in rows[1]["files"]] == [
        ("DOCX", True),
        ("PDF", True),
    ]
    only_tables = client.get(generations_url(scenario.process), params={"kind": "TABELA"}).json()
    assert [r["id"] for r in only_tables] == [ready["id"]]


def test_the_list_gives_each_table_the_version_of_the_scoring_table_it_used(
    client, scenario, scoring_tables
):
    # GI-11: the running row has no snapshot yet, the ready table has the chosen version
    ready = generate(client, scenario.headers, scenario.process, "TABELA")
    assert ask(client, scenario.headers, scenario.process, "TABELA").status_code == 202

    rows = client.get(generations_url(scenario.process), params={"kind": "TABELA"}).json()

    assert [(r["state"], r["table_version_id"]) for r in rows] == [
        ("GERANDO", None),
        ("PRONTO", str(scoring_tables["OFICIAL"].id)),
    ]
    assert rows[1]["id"] == ready["id"]


def test_the_detail_of_a_ready_version_has_the_summary_of_what_it_used(client, scenario):
    ready = generate(client, scenario.headers, scenario.process, "TABELA")

    body = client.get(f"/api/generated-documents/{ready['id']}").json()

    scored = client.get(f"/api/processes/{scenario.process['id']}/scoring").json()
    assert body["summary"]["total"] == scored["total"]
    assert body["summary"]["activity_count"] == 1
    assert (body["summary"]["interstice_start"], body["summary"]["interstice_end"]) == (
        "2022-11-23",
        "2024-11-23",
    )


@pytest.mark.parametrize(
    ("extension", "content_type", "magic"),
    [("docx", DOCX, b"PK"), ("pdf", "application/pdf", b"%PDF")],
)
def test_the_download_gives_the_stored_file_with_its_type_a_plain_name_and_the_sha256_etag(
    client, scenario, extension, content_type, magic
):
    ready = generate(client, scenario.headers, scenario.process, "TABELA")

    response = client.get(file_url(ready, extension))

    assert response.status_code == 200
    assert response.headers["content-type"] == content_type
    assert response.headers["content-disposition"] == (
        f"attachment; filename*=UTF-8''Tabela_de_Pontuacao_2022-2024_v1.{extension}"
    )
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["etag"] == f'"{sha256(response.content)}"'
    stored = next(f for f in ready["files"] if f["format"] == extension.upper())
    assert response.headers["etag"] == f'"{stored["sha256"]}"'
    assert (len(response.content), response.content[:4].startswith(magic)) == (
        stored["size_bytes"],
        True,
    )
    assert "Maria" not in response.headers["content-disposition"]


def test_a_row_still_running_an_unknown_format_and_an_unknown_row_are_404(client, scenario):
    waiting = ask(client, scenario.headers, scenario.process).json()
    ready_row = {"id": waiting["id"]}

    assert client.get(file_url(ready_row, "pdf")).status_code == 404
    run_executor(client)
    assert client.get(file_url(ready_row, "pdf")).status_code == 200
    assert client.get(file_url(ready_row, "xlsx")).status_code == 404
    assert client.get(file_url({"id": uuid.uuid4()}, "pdf")).status_code == 404
    assert client.get(f"/api/generated-documents/{uuid.uuid4()}").status_code == 404


def test_without_access_to_the_process_every_route_is_404(client, scenario, act_as, reference):
    ready = generate(client, scenario.headers, scenario.process, "TABELA")
    _, outsider = act_as(
        "fora@ufpa.br", Role.SECRETARIA, unit_ids=frozenset({reference["IFCH"].id})
    )

    assert ask(client, outsider, scenario.process).status_code == 404
    assert client.get(generations_url(scenario.process)).status_code == 404
    assert client.get(f"/api/generated-documents/{ready['id']}").status_code == 404
    assert client.get(file_url(ready, "pdf")).status_code == 404


def test_a_concluded_process_still_downloads_and_refuses_only_the_comprovante(
    client, scenario, uow_factory
):
    ready = generate(client, scenario.headers, scenario.process, "TABELA")
    link_deleted_original(uow_factory, scenario.process, scenario.user, scenario.activity)
    conclude_for_test(uow_factory, scenario.process["id"])

    download = client.get(file_url(ready, "pdf"))
    table = ask(client, scenario.headers, scenario.process, "TABELA")
    comprovante = ask(client, scenario.headers, scenario.process, "COMPROVANTE")

    assert download.status_code == 200
    assert table.status_code == 202
    assert comprovante.status_code == 422
    [detail] = comprovante.json()["detail"]
    assert (detail["field"], detail["code"]) == ("geracao", "ORIGINAIS_EXCLUIDOS")


def test_no_response_carries_a_file_path_a_stored_name_or_the_professor(client, scenario, tmp_path):
    ready = generate(client, scenario.headers, scenario.process, "TABELA")

    texts = [
        client.get(generations_url(scenario.process)).text,
        client.get(f"/api/generated-documents/{ready['id']}").text,
    ]

    for text in texts:
        assert str(tmp_path) not in text
        assert "internal_name" not in text and '.docx"' not in text
        assert "Maria Docente" not in text
