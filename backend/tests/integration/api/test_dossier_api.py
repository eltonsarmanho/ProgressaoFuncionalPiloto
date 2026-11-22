"""DOS-01 to DOS-06, BNAV-02, BNAV-03: the checklist of the dossier of a process and the mark
"Entregue" (synthetic data only)."""

import uuid
from types import SimpleNamespace

import pytest

from app.domain.entities.generated import DocumentKind
from app.domain.entities.process import ProcessStatus
from tests.integration.api.board_support import as_user, board_url, set_status
from tests.integration.api.generated_support import add_ready, choose_table
from tests.integration.documents.generated_support import T0, make_file, make_generation

K = DocumentKind
ORDER = [
    "REQUERIMENTO",
    "PORTARIA_ULTIMA_PROGRESSAO",
    "DECLARACAO_EXERCICIOS_ANTERIORES",
    "RELATORIO",
    "TABELA",
    "COMPROVANTE",
    "CURRICULO_LATTES",
    "PORTARIA_BANCA",
    "PARECER",
]
MANUAL = ["PORTARIA_ULTIMA_PROGRESSAO", "DECLARACAO_EXERCICIOS_ANTERIORES", "CURRICULO_LATTES"]


def dossier_url(process, tail: str = "") -> str:
    return f"/api/processes/{process['id']}/dossier{tail}"


def states(client, process) -> dict:
    response = client.get(dossier_url(process))
    assert response.status_code == 200, response.text
    return {item["key"]: item["state"] for item in response.json()}


def deliver(client, process, headers, key="CURRICULO_LATTES", **body):
    return client.put(
        dossier_url(process, f"/items/{key}"), json=body or {"entregue": True}, headers=headers
    )


def add_three_ready(uow_factory, process, user):
    for kind in (K.TABELA, K.RELATORIO, K.COMPROVANTE):
        add_ready(uow_factory, process, user, kind)


def add_table_made_with(uow_factory, process, user, version_id):
    row = make_generation(SimpleNamespace(id=uuid.UUID(process["id"])), user.id, K.TABELA)
    with uow_factory() as uow:
        uow.generations.add(row)
        uow.generations.finish_ready(
            row.id, T0, [make_file()], {"total": "1", "table_version": {"id": str(version_id)}}, ()
        )
        uow.commit()


# --- GET /dossier ---------------------------------------------------------------------------------


def test_a_process_with_only_the_table_the_report_and_the_comprovante_has_three_ready_six_pending(
    client, process, admin, uow_factory
):
    add_three_ready(uow_factory, process, admin[0])

    response = client.get(dossier_url(process))

    assert response.status_code == 200
    items = response.json()
    assert [i["key"] for i in items] == ORDER
    assert [i["order"] for i in items] == list(range(1, 10))
    assert {i["key"] for i in items if i["state"] == "GERADO"} == {
        "RELATORIO",
        "TABELA",
        "COMPROVANTE",
    }
    assert sorted(i["key"] for i in items if i["state"] == "PENDENTE") == sorted(
        set(ORDER) - {"RELATORIO", "TABELA", "COMPROVANTE"}
    )
    assert {i["key"]: i["source"] for i in items} == {
        "REQUERIMENTO": "GERADO",
        "PORTARIA_ULTIMA_PROGRESSAO": "MANUAL",
        "DECLARACAO_EXERCICIOS_ANTERIORES": "MANUAL",
        "RELATORIO": "GERADO",
        "TABELA": "GERADO",
        "COMPROVANTE": "GERADO",
        "CURRICULO_LATTES": "MANUAL",
        "PORTARIA_BANCA": "PORTARIA_BANCA",
        "PARECER": "GERADO",
    }
    assert {i["key"] for i in items if i["title"]} == set(ORDER)


def test_a_ready_item_carries_the_last_version_number_and_the_id_to_download(
    client, process, admin, uow_factory
):
    add_ready(uow_factory, process, admin[0], K.RELATORIO)
    add_ready(uow_factory, process, admin[0], K.RELATORIO)

    item = next(i for i in client.get(dossier_url(process)).json() if i["key"] == "RELATORIO")

    assert (item["state"], item["version_number"]) == ("GERADO", 2)
    with uow_factory() as uow:
        newest = uow.generations.latest_ready_by_kind(uuid.UUID(process["id"]))[K.RELATORIO]
    assert item["generation_id"] == str(newest.id)
    pending = next(i for i in client.get(dossier_url(process)).json() if i["key"] == "PARECER")
    assert (pending["version_number"], pending["generation_id"]) == (None, None)


def test_the_parecer_and_the_requerimento_ready_are_shown_as_generated(
    client, process, admin, uow_factory
):
    add_ready(uow_factory, process, admin[0], K.REQUERIMENTO)
    add_ready(uow_factory, process, admin[0], K.PARECER)

    result = states(client, process)

    assert (result["REQUERIMENTO"], result["PARECER"]) == ("GERADO", "GERADO")


def test_the_ordinance_with_a_member_is_registered(client, process, headers):
    assert states(client, process)["PORTARIA_BANCA"] == "PENDENTE"
    saved = client.put(
        board_url(process, "/ordinance"),
        json={"members": [{"name": "Ana Souza", "role": "PRESIDENTE"}], "expected_version": 0},
        headers=headers,
    )
    assert saved.status_code == 200

    assert states(client, process)["PORTARIA_BANCA"] == "REGISTRADA"


def test_a_table_made_with_another_version_of_the_table_is_outdated(
    client, process, admin, headers, scoring_tables, uow_factory
):
    choose_table(client, headers, process, scoring_tables["OFICIAL"])
    add_table_made_with(uow_factory, process, admin[0], scoring_tables["OUTRA"].id)

    table = next(i for i in client.get(dossier_url(process)).json() if i["key"] == "TABELA")

    assert (table["state"], table["outdated_table"]) == ("GERADO", True)
    choose_table(client, headers, process, scoring_tables["OUTRA"])
    table = next(i for i in client.get(dossier_url(process)).json() if i["key"] == "TABELA")
    assert table["outdated_table"] is False


# --- PUT /dossier/items/{key} ---------------------------------------------------------------------


def test_marking_the_lattes_returns_the_new_list_and_survives_a_reload(client, process, headers):
    response = deliver(client, process, headers)

    assert response.status_code == 200
    assert {i["key"]: i["state"] for i in response.json()}["CURRICULO_LATTES"] == "ENTREGUE"
    assert states(client, process)["CURRICULO_LATTES"] == "ENTREGUE"


def test_unmarking_goes_back_to_pending_and_repeating_either_is_harmless(client, process, headers):
    deliver(client, process, headers)
    deliver(client, process, headers)

    unmarked = deliver(client, process, headers, entregue=False)
    again = deliver(client, process, headers, entregue=False)

    assert unmarked.status_code == again.status_code == 200
    assert states(client, process)["CURRICULO_LATTES"] == "PENDENTE"


@pytest.mark.parametrize("key", ["TABELA", "PORTARIA_BANCA", "REQUERIMENTO", "NAO_EXISTE"])
def test_a_key_that_is_not_manual_or_does_not_exist_is_a_422_on_key(client, process, headers, key):
    response = deliver(client, process, headers, key)

    assert response.status_code == 422
    assert response.json()["detail"][0]["field"] == "key"
    assert set(states(client, process).values()) == {"PENDENTE"}


def test_a_body_without_entregue_or_with_another_field_is_a_422(client, process, headers):
    empty = client.put(dossier_url(process, "/items/CURRICULO_LATTES"), json={}, headers=headers)
    extra = deliver(client, process, headers, entregue=True, justificativa="x")

    assert empty.status_code == 422 and empty.json()["detail"][0]["field"] == "entregue"
    assert extra.status_code == 422
    assert states(client, process)["CURRICULO_LATTES"] == "PENDENTE"


@pytest.mark.parametrize("status", [ProcessStatus.CONCLUIDO, ProcessStatus.ARQUIVADO])
def test_a_closed_process_refuses_the_mark_with_409_and_still_reads(
    client, process, headers, uow_factory, status
):
    deliver(client, process, headers, "PORTARIA_ULTIMA_PROGRESSAO")
    set_status(uow_factory, process, status)

    marked = deliver(client, process, headers)
    unmarked = deliver(client, process, headers, "PORTARIA_ULTIMA_PROGRESSAO", entregue=False)

    for response in (marked, unmarked):
        assert response.status_code == 409
        assert response.json()["code"] == "PROCESSO_SOMENTE_LEITURA"
    result = states(client, process)
    assert result["PORTARIA_ULTIMA_PROGRESSAO"] == "ENTREGUE"
    assert result["CURRICULO_LATTES"] == "PENDENTE"


# --- BNAV-03 and session --------------------------------------------------------------------------


def test_without_access_to_the_process_both_routes_are_404(client, process, actors):
    for outsider in (actors.other_docente, actors.other_secretaria):
        outsider_headers = as_user(client, outsider)

        assert client.get(dossier_url(process)).status_code == 404
        assert deliver(client, process, outsider_headers).status_code == 404
    as_user(client, actors.owner)
    assert states(client, process)["CURRICULO_LATTES"] == "PENDENTE"


@pytest.mark.parametrize("who", ["owner", "secretaria"])
def test_the_owner_and_the_secretary_of_the_unit_read_and_mark(client, process, actors, who):
    user_headers = as_user(client, getattr(actors, who))

    assert client.get(dossier_url(process)).status_code == 200
    assert deliver(client, process, user_headers).status_code == 200


def test_without_a_session_both_routes_are_401(make_client, process):
    anonymous = make_client()

    assert anonymous.get(dossier_url(process)).status_code == 401
    assert (
        anonymous.put(dossier_url(process, "/items/CURRICULO_LATTES"), json={"entregue": True})
    ).status_code == 401


# --- compatibility --------------------------------------------------------------------------------


def test_the_order_route_keeps_its_format_and_the_same_order_as_the_checklist(
    client, process, admin
):
    order = client.get("/api/dossier-order")

    assert order.status_code == 200
    assert all(set(item) == {"order", "title", "generated_by"} for item in order.json())
    checklist = client.get(dossier_url(process)).json()
    assert [(i["order"], i["title"]) for i in order.json()] == [
        (i["order"], i["title"]) for i in checklist
    ]
