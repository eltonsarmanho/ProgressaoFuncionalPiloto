"""VINC-02, VINC-03, VINC-05 (T39): evidence routes and the evidences of the activity JSON."""

import uuid
from types import SimpleNamespace

import pytest

from app.domain.entities.user import Role
from tests.integration.api.documents_support import finish_processing, seed_run, upload
from tests.integration.api.factories import process_payload
from tests.integration.api.test_documents_api import close_process
from tests.support import synthetic_docs as synth

EVIDENCE_KEYS = {"id", "document_id", "document_name", "page", "excerpt"}


def evidences_url(activity):
    return f"/api/activities/{activity['id']}/evidences"


def new_activity(client, headers, process, title="Banca de TCC"):
    response = client.post(
        f"/api/processes/{process['id']}/activities",
        json={"title": title, "group_number": 3, "item_number": 4, "event_date": "2023-05-10"},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def link(client, headers, activity, document, page=1, **extra):
    return client.post(
        evidences_url(activity),
        json={"document_id": document["id"], "page": page, **extra},
        headers=headers,
    )


@pytest.fixture
def two_page_document(client, headers, process, uow_factory):
    """A processed two-page document with the stored text of each page."""
    content = synth.pdf_with_text(["Texto da primeira pagina", "Declaracao de banca"])
    document = upload(client, headers, process, ("comprovante.pdf", content)).json()[0]["document"]
    finish_processing(uow_factory, document)
    seed_run(
        uow_factory,
        SimpleNamespace(id=uuid.UUID(document["id"])),
        texts=("Texto da primeira pagina", "Declaracao de banca " * 30),
    )
    return document


# --- link, list and remove --------------------------------------------------------------------


def test_link_is_201_with_the_evidence_and_the_page_excerpt(
    client, headers, process, two_page_document
):
    activity = new_activity(client, headers, process)

    response = link(client, headers, activity, two_page_document, page=2)

    assert response.status_code == 201, response.text
    body = response.json()
    assert set(body) == EVIDENCE_KEYS
    assert body["document_id"] == two_page_document["id"]
    assert body["document_name"] == "comprovante.pdf"
    assert body["page"] == 2
    assert body["excerpt"] == ("Declaracao de banca " * 30).strip()[:300]


def test_the_linked_documents_appear_in_the_activity_detail_and_in_the_list_and_removal_clears_them(
    client, headers, process, two_page_document
):
    activity = new_activity(client, headers, process)
    other = new_activity(client, headers, process, "Outra")
    assert client.get(f"/api/activities/{activity['id']}").json()["evidences"] == []
    created = link(client, headers, activity, two_page_document, page=1).json()

    detail = client.get(f"/api/activities/{activity['id']}").json()
    listed = {
        a["id"]: a
        for a in client.get(f"/api/processes/{process['id']}/activities").json()
    }

    assert detail["evidences"] == [created]
    assert listed[activity["id"]]["evidences"] == [created]
    assert listed[other["id"]]["evidences"] == []

    removed = client.delete(f"{evidences_url(activity)}/{created['id']}", headers=headers)

    assert removed.status_code == 204
    assert removed.content == b""
    after = client.get(f"/api/activities/{activity['id']}").json()
    assert after["evidences"] == []
    assert after["id"] == activity["id"]  # the activity stays


def test_every_activity_response_carries_its_evidences(
    client, headers, process, two_page_document
):
    activity = new_activity(client, headers, process)
    created = link(client, headers, activity, two_page_document).json()
    current = client.get(f"/api/activities/{activity['id']}").json()
    body = {"title": "Banca renomeada", "group_number": 3, "item_number": 4,
            "event_date": "2023-05-10", "expected_version": current["version"],
            "justificativa": "Corrigindo o titulo"}  # fmt: skip

    updated = client.put(f"/api/activities/{activity['id']}", json=body, headers=headers)

    assert updated.status_code == 200, updated.text
    assert updated.json()["evidences"] == [created]


def test_an_activity_created_through_the_api_starts_without_evidences(client, headers, process):
    assert new_activity(client, headers, process)["evidences"] == []


# --- VINC-03: a document already linked to another activity --------------------------------


def test_linking_a_document_already_linked_elsewhere_needs_no_justification(
    client, headers, process, two_page_document
):
    first = new_activity(client, headers, process, "Primeira")
    second = new_activity(client, headers, process, "Segunda")
    assert link(client, headers, first, two_page_document).status_code == 201

    plain = link(client, headers, second, two_page_document)  # UIM-16: no justification
    with_reason = link(
        client, headers, second, two_page_document, page=2, justificativa="O mesmo documento"
    )

    assert plain.status_code == 201
    assert with_reason.status_code == 201
    assert len(client.get(f"/api/activities/{second['id']}").json()["evidences"]) == 2


def test_the_same_activity_document_and_page_twice_is_409(
    client, headers, process, two_page_document
):
    activity = new_activity(client, headers, process)
    link(client, headers, activity, two_page_document, page=1)

    again = link(client, headers, activity, two_page_document, page=1)
    other_page = link(client, headers, activity, two_page_document, page=2)

    assert again.status_code == 409
    assert other_page.status_code == 201


@pytest.mark.parametrize("page", [0, 3])
def test_a_page_outside_the_document_is_422_on_pagina(
    client, headers, process, two_page_document, page
):
    # the document has two pages
    activity = new_activity(client, headers, process)

    response = link(client, headers, activity, two_page_document, page=page)

    assert response.status_code == 422
    assert response.json()["detail"][0]["field"] == "pagina"


def test_a_document_of_another_process_is_422_on_documento(
    client, admin, headers, process, professor, two_page_document
):
    other_process = client.post(
        "/api/processes", json=process_payload(professor), headers=headers
    ).json()
    foreign = new_activity(client, headers, other_process)

    response = link(client, headers, foreign, two_page_document)

    assert response.status_code == 422
    assert response.json()["detail"][0]["field"] == "documento"


def test_a_missing_field_is_422_on_that_field(client, headers, process):
    activity = new_activity(client, headers, process)

    no_page = client.post(evidences_url(activity), json={"document_id": str(uuid.uuid4())},
                          headers=headers)  # fmt: skip

    assert no_page.status_code == 422
    assert no_page.json()["detail"][0]["field"] == "page"


# --- access --------------------------------------------------------------------------------


def test_unknown_ids_are_404(client, headers, process, two_page_document):
    activity = new_activity(client, headers, process)

    unknown_activity = client.post(
        f"/api/activities/{uuid.uuid4()}/evidences",
        json={"document_id": two_page_document["id"], "page": 1},
        headers=headers,
    )
    unknown_document = client.post(
        evidences_url(activity), json={"document_id": str(uuid.uuid4()), "page": 1}, headers=headers
    )
    unknown_link = client.delete(f"{evidences_url(activity)}/{uuid.uuid4()}", headers=headers)

    assert [r.status_code for r in (unknown_activity, unknown_document, unknown_link)] == [404] * 3


def test_a_link_of_another_activity_cannot_be_removed_through_this_one(
    client, headers, process, two_page_document
):
    mine = new_activity(client, headers, process, "Minha")
    theirs = new_activity(client, headers, process, "Outra")
    created = link(client, headers, theirs, two_page_document).json()

    response = client.delete(f"{evidences_url(mine)}/{created['id']}", headers=headers)

    assert response.status_code == 404
    assert len(client.get(f"/api/activities/{theirs['id']}").json()["evidences"]) == 1


def test_evidence_routes_need_a_session_the_csrf_token_and_access(
    client, make_client, act_as, headers, process, two_page_document, reference
):
    activity = new_activity(client, headers, process)
    created = link(client, headers, activity, two_page_document).json()
    body = {"document_id": two_page_document["id"], "page": 2}
    anonymous = make_client()
    no_csrf = (
        client.post(evidences_url(activity), json=body),
        client.delete(f"{evidences_url(activity)}/{created['id']}"),
    )
    _, other = act_as("fora@ufpa.br", Role.SECRETARIA, unit_ids=frozenset({reference["IFCH"].id}))

    assert [r.status_code for r in no_csrf] == [403, 403]
    assert anonymous.post(evidences_url(activity), json=body).status_code == 401
    assert anonymous.delete(f"{evidences_url(activity)}/{created['id']}").status_code == 401
    assert client.post(evidences_url(activity), json=body, headers=other).status_code == 404
    deleted = client.delete(f"{evidences_url(activity)}/{created['id']}", headers=other)
    assert deleted.status_code == 404
    assert client.get(f"/api/activities/{activity['id']}").status_code == 404


def test_links_on_a_closed_process_are_409(
    client, headers, process, two_page_document, uow_factory
):
    activity = new_activity(client, headers, process)
    created = link(client, headers, activity, two_page_document).json()
    close_process(client, headers, process, uow_factory)

    assert link(client, headers, activity, two_page_document, page=2).status_code == 409
    removed = client.delete(f"{evidences_url(activity)}/{created['id']}", headers=headers)
    assert removed.status_code == 409
