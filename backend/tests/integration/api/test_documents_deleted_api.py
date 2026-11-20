"""DEL-12, DEL-06 (T88): a document whose input file the conclusion removed is flagged
`arquivo_excluido` and answers 410 `ARQUIVO_EXCLUIDO` where a file or a page text is needed."""

import uuid

import pytest

from app.domain.entities.user import Role
from tests.integration.api.documents_support import pdf, seed_run, upload_one
from tests.integration.api.factories import process_payload
from tests.integration.api.generated_support import process_url
from tests.support.process_status import conclude_for_test


@pytest.fixture
def pair(client, scenario, uow_factory, professor):
    """A document of the process that the conclusion's purge removes (`purged`, with two pages and
    the activity of the scenario linked to page 1) and an ordinary document of another process
    (`kept`)."""
    other = client.post(
        "/api/processes", json=process_payload(professor), headers=scenario.headers
    ).json()
    kept = upload_one(client, scenario.headers, other, "mantido")
    purged = upload_one(client, scenario.headers, scenario.process, "excluido")
    with uow_factory() as uow:
        row = uow.documents.get(uuid.UUID(purged["id"]))
    seed_run(uow_factory, row, texts=("texto da primeira", "texto da segunda"), warnings=())
    link = client.post(
        f"/api/activities/{scenario.activity['id']}/evidences",
        json={"document_id": purged["id"], "page": 1},
        headers=scenario.headers,
    )
    assert link.status_code == 201, link.text
    scenario.kept, scenario.purged, scenario.other = kept, purged, other
    return scenario


def purge(client, scenario) -> None:
    client.app.state.container.conclude_process._purge.execute(uuid.UUID(scenario.process["id"]))


def test_the_list_and_the_detail_flag_the_purged_document_and_not_an_ordinary_one(client, pair):
    before = client.get(f"/api/documents/{pair.purged['id']}").json()
    purge(client, pair)

    listed = {d["id"]: d for d in client.get(process_url(pair.process, "documents")).json()}
    detail = client.get(f"/api/documents/{pair.purged['id']}").json()
    other = client.get(f"/api/documents/{pair.kept['id']}").json()

    assert before["arquivo_excluido"] is False
    assert listed[pair.purged["id"]]["arquivo_excluido"] is True
    assert (detail["arquivo_excluido"], other["arquivo_excluido"]) == (True, False)
    [ordinary] = client.get(process_url(pair.other, "documents")).json()
    assert ordinary["arquivo_excluido"] is False
    # the pages of a purged document are no longer shown, the metadata and the link stay
    assert detail["pages"] == []
    assert [e["page"] for a in detail["activities"] for e in a["evidences"]] == [1]
    assert [e["excerpt"] for a in detail["activities"] for e in a["evidences"]] == [""]


@pytest.mark.parametrize("query", ["", "?download=true"])
def test_the_file_of_a_purged_document_is_410_with_field_code_and_message(client, pair, query):
    purge(client, pair)

    response = client.get(f"/api/documents/{pair.purged['id']}/file{query}")

    assert response.status_code == 410
    [detail] = response.json()["detail"]
    assert (detail["field"], detail["code"]) == ("arquivo", "ARQUIVO_EXCLUIDO")
    assert detail["message"]


def test_an_ordinary_document_still_serves_its_file_and_its_pages(client, pair):
    served = client.get(f"/api/documents/{pair.kept['id']}/file")

    assert served.status_code == 200
    assert served.content == pdf("mantido")
    seeded = client.get(f"/api/documents/{pair.purged['id']}").json()
    assert [p["text"] for p in seeded["pages"]] == ["texto da primeira", "texto da segunda"]


def test_replacing_reprocessing_and_linking_a_purged_document_are_410(client, pair):
    purge(client, pair)
    document = pair.purged["id"]

    reprocess = client.post(f"/api/documents/{document}/reprocess", headers=pair.headers)
    replace = client.put(
        f"/api/documents/{document}/file",
        files={"file": ("novo.pdf", pdf("novo"), "application/pdf")},
        headers=pair.headers,
    )
    other = client.post(
        process_url(pair.process, "activities"),
        json={
            "title": "Outra",
            "group_number": 2,
            "item_number": 7,
            "quantidade": 1,
            "event_date": "2023-05-10",
            "evidence_note": "x",
        },
        headers=pair.headers,
    ).json()
    link = client.post(
        f"/api/activities/{other['id']}/evidences",
        json={"document_id": document, "page": 2},
        headers=pair.headers,
    )

    for response in (reprocess, replace, link):
        assert response.status_code == 410, response.text
        assert response.json()["detail"][0]["code"] == "ARQUIVO_EXCLUIDO"


def test_in_a_concluded_process_the_purged_file_is_still_410_not_read_only(
    client, pair, uow_factory
):
    purge(client, pair)
    conclude_for_test(uow_factory, pair.process["id"])

    file = client.get(f"/api/documents/{pair.purged['id']}/file")
    reprocess = client.post(f"/api/documents/{pair.purged['id']}/reprocess", headers=pair.headers)

    assert (file.status_code, reprocess.status_code) == (410, 410)


def test_without_access_to_the_process_a_purged_document_is_404_not_410(
    client, pair, act_as, reference
):
    purge(client, pair)
    act_as("fora@ufpa.br", Role.SECRETARIA, unit_ids=frozenset({reference["IFCH"].id}))

    assert client.get(f"/api/documents/{pair.purged['id']}/file").status_code == 404
    assert client.get(f"/api/documents/{pair.purged['id']}").status_code == 404
