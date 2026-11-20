"""FORA-02, FORA-03, FORA-04, FORA-08: the API of a document outside the interstice.

The process interstice is 2022-11-23 to 2024-11-23 (the `case` of the documents flow); the
document of 2020 is outside it and the one of 2023 is inside. The AI is the simulated MariTalk.
"""

import json
from dataclasses import replace
from datetime import date

import httpx
import pytest

from tests.integration.api.test_documents_flow import (  # noqa: F401  (fixtures and helpers)
    MariTalkServer,
    activities,
    case,
    detail,
    drain,
    flat,
    score,
    text_pdf,
    upload,
)
from tests.unit.application.analyzer_fakes import activity, payload

PROFESSOR = "Maria Docente da Silva"
OUTSIDE = "DOCUMENTO_FORA_DO_INTERSTICIO"


def banca(when: str, title: str) -> str:
    return (
        "DECLARACAO DE BANCA EXAMINADORA\n"
        f"Declaramos que {PROFESSOR}, matricula SIAPE 1234567, participou como membro da banca "
        f"examinadora do trabalho de conclusao de curso {title}, realizada em {when}, "
        "na Faculdade Exemplo de Testes."
    )


OLD = banca("12 de marco de 2020", "Estudo Antigo sobre Dados Abertos")
CURRENT = banca("12 de marco de 2023", "Estudo Atual sobre Dados Abertos")


class DatedServer(MariTalkServer):
    """Answers a banca dated by the year written in the text."""

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        text = flat(json.loads(request.content)["messages"][-1]["content"])
        old = "2020" in text
        answer = payload(
            activity(
                title="Estudo Antigo sobre Dados Abertos"
                if old
                else "Estudo Atual sobre Dados Abertos",
                event_date="2020-03-12" if old else "2023-03-12",
            ),
            name=PROFESSOR,
        )
        choice = {"message": {"content": json.dumps(answer)}, "finish_reason": "stop"}
        return httpx.Response(200, json={"choices": [choice]})


@pytest.fixture
def ai():
    return DatedServer()


@pytest.fixture
def both(case):  # noqa: F811
    """(client, headers, process, outside document, inside document), already processed."""
    client, headers, process = case
    old, current = upload(
        client, headers, process, ("antigo.pdf", text_pdf(OLD)), ("atual.pdf", text_pdf(CURRENT))
    )
    assert drain(client) == 2
    return client, headers, process, old, current


def listed(client, process):
    response = client.get(f"/api/processes/{process['id']}/documents")
    assert response.status_code == 200, response.text
    return {d["original_name"]: d for d in response.json()}


def test_the_list_flags_the_outside_document_with_its_date_and_the_interstice(both):
    client, _, process, _, _ = both

    rows = listed(client, process)

    old = rows["antigo.pdf"]
    assert old["outside_interstice"] is True
    assert (old["status"], old["status_code"]) == ("PROCESSADO", OUTSIDE)
    assert old["document_date"] == "2020-03-12"
    assert old["document_date_precision"] == "DAY"
    assert (old["interstice_start"], old["interstice_end"]) == ("2022-11-23", "2024-11-23")
    assert old["activity_count"] == 0


def test_a_document_inside_the_interstice_carries_no_outside_fields(both):
    client, _, process, _, _ = both

    current = listed(client, process)["atual.pdf"]

    assert current["outside_interstice"] is False
    assert current["status_code"] is None
    assert current["document_date"] is None
    assert current["interstice_start"] is None
    assert current["activity_count"] == 1


def test_the_detail_lists_the_alert_with_its_detail(both):
    client, _, _, old, _ = both

    [alert] = [a for a in detail(client, old)["alerts"] if a["code"] == OUTSIDE]

    assert alert["detail"] == {
        "document_date": "2020-03-12",
        "date_precision": "DAY",
        "interstice_start": "2022-11-23",
        "interstice_end": "2024-11-23",
    }


def test_the_outside_document_reaches_no_activity_no_score_row_and_no_link(both):
    client, _, process, old, current = both

    found = activities(client, process)
    scoring = json.dumps(score(client, process))

    assert [a["title"] for a in found] == ["Estudo Atual sobre Dados Abertos"]
    assert {e["document_id"] for a in found for e in a["evidences"]} == {current["id"]}
    assert old["id"] not in scoring
    assert "antigo.pdf" not in scoring
    assert "Estudo Antigo" not in scoring


def test_classifying_an_outside_document_is_409_with_its_code(both):
    client, headers, _, old, _ = both

    response = client.put(
        f"/api/documents/{old['id']}/classification",
        json={"tipo": "CERTIFICADO", "categoria": "CURSO_CONCLUIDO"},
        headers=headers,
    )

    assert response.status_code == 409
    assert response.json()["code"] == OUTSIDE


def test_linking_an_activity_to_an_outside_document_is_409_with_its_code(both):
    client, headers, process, old, _ = both
    [draft] = activities(client, process)

    response = client.post(
        f"/api/activities/{draft['id']}/evidences",
        json={"document_id": old["id"], "page": 1},
        headers=headers,
    )

    assert response.status_code == 409
    assert response.json()["code"] == OUTSIDE


def test_an_outside_document_still_downloads_reprocesses_and_deletes(both):
    client, headers, _, old, _ = both

    assert client.get(f"/api/documents/{old['id']}/file").status_code == 200
    assert client.post(f"/api/documents/{old['id']}/reprocess", headers=headers).status_code == 202
    assert client.delete(f"/api/documents/{old['id']}", headers=headers).status_code == 204


def test_narrowing_the_interstice_and_reprocessing_retires_the_old_draft_without_new_rows(case):  # noqa: F811
    client, headers, process = case
    [current] = upload(client, headers, process, ("atual.pdf", text_pdf(CURRENT)))
    drain(client)
    assert [a["status"] for a in activities(client, process)] == ["AGUARDANDO_REVISAO"]
    container = client.app.state.container
    with container.uow_factory() as uow:  # the interstice moves past the document (2023)
        stored = uow.processes.get(process["id"])
        moved = replace(stored, start_date=date(2024, 11, 24), end_date=date(2026, 11, 23))
        uow.processes.update(moved, stored.version)
        uow.commit()

    reprocessed = client.post(f"/api/documents/{current['id']}/reprocess", headers=headers)
    assert reprocessed.status_code == 202
    drain(client)

    row = listed(client, process)["atual.pdf"]
    assert (row["outside_interstice"], row["activity_count"]) == (True, 0)
    assert [a["status"] for a in activities(client, process)] == ["REJEITADA"]
    # SEG-01: the retired draft stays rejected, so it is not valid and has no score row
    assert score(client, process)["rows"] == []


def test_a_validated_activity_leaves_every_stage_when_reprocessing_puts_its_document_outside(
    case,  # noqa: F811
):
    client, headers, process = case
    [current] = upload(client, headers, process, ("atual.pdf", text_pdf(CURRENT)))
    drain(client)
    [draft] = activities(client, process)
    validated = client.post(
        f"/api/activities/{draft['id']}/status",
        json={"status": "VALIDADA", "expected_version": draft["version"]},
        headers=headers,
    )
    assert validated.status_code == 200, validated.text
    container = client.app.state.container
    with container.uow_factory() as uow:  # the interstice moves past the document (2023)
        stored = uow.processes.get(process["id"])
        moved = replace(stored, start_date=date(2024, 11, 24), end_date=date(2026, 11, 23))
        uow.processes.update(moved, stored.version)
        uow.commit()

    reprocessed = client.post(f"/api/documents/{current['id']}/reprocess", headers=headers)
    assert reprocessed.status_code == 202
    drain(client)

    row = listed(client, process)["atual.pdf"]
    assert (row["outside_interstice"], row["activity_count"]) == (True, 0)
    [rejected] = activities(client, process)
    assert rejected["status"] == "REJEITADA"
    # SEG-01: the rejected activity is not valid and has no score row
    assert score(client, process)["rows"] == []
    assert score(client, process)["total"] == "0.00"
