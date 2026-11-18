"""DOC-11, PIPE-09 (T38): reprocess and manual classification routes."""

import uuid

import pytest

from app.domain.entities.user import Role
from tests.integration.api.documents_support import finish_processing, upload_one
from tests.integration.api.test_documents_api import close_process


def reprocess_url(document):
    return f"/api/documents/{document['id']}/reprocess"


def classification_url(document):
    return f"/api/documents/{document['id']}/classification"


def processed(client, headers, process, uow_factory, label="processado"):
    document = upload_one(client, headers, process, label)
    finish_processing(uow_factory, document)
    return client.get(f"/api/documents/{document['id']}").json()


def active_job(uow_factory, document):
    with uow_factory() as uow:
        return uow.jobs.active_for_document(uuid.UUID(document["id"]))


# --- reprocess: PIPE-09 ----------------------------------------------------------------------


def test_reprocess_is_202_with_the_document_pending_and_queues_one_job(
    client, headers, process, uow_factory
):
    document = processed(client, headers, process, uow_factory)
    assert active_job(uow_factory, document) is None

    response = client.post(reprocess_url(document), headers=headers)

    assert response.status_code == 202
    body = response.json()
    assert body["id"] == document["id"]
    assert body["status"] == "PENDENTE"
    assert body["version"] > document["version"]
    assert active_job(uow_factory, document).status.value == "PENDENTE"
    assert client.get(f"/api/documents/{document['id']}").json()["status"] == "PENDENTE"


def test_a_second_reprocess_while_the_first_is_queued_is_409(
    client, headers, process, uow_factory
):
    document = processed(client, headers, process, uow_factory)

    first = client.post(reprocess_url(document), headers=headers)
    second = client.post(reprocess_url(document), headers=headers)

    assert first.status_code == 202
    assert second.status_code == 409
    with uow_factory() as uow:  # still exactly one job in the queue
        assert uow.jobs.active_for_document(uuid.UUID(document["id"])) is not None


def test_a_document_still_in_the_queue_cannot_be_reprocessed(client, headers, process):
    document = upload_one(client, headers, process, "na-fila")

    assert client.post(reprocess_url(document), headers=headers).status_code == 409


def test_reprocess_on_a_closed_process_is_409(client, headers, process, uow_factory):
    document = processed(client, headers, process, uow_factory)
    close_process(client, headers, process, uow_factory)

    assert client.post(reprocess_url(document), headers=headers).status_code == 409


def test_reprocess_and_classify_need_a_session_the_csrf_token_and_access(
    client, make_client, act_as, headers, process, uow_factory, reference
):
    document = processed(client, headers, process, uow_factory)
    anonymous = make_client()
    body = {"tipo": "CERTIFICADO", "categoria": "CURSO_CONCLUIDO"}
    no_csrf = (
        client.post(reprocess_url(document)),
        client.put(classification_url(document), json=body),
    )
    _, other = act_as("fora@ufpa.br", Role.SECRETARIA, unit_ids=frozenset({reference["IFCH"].id}))

    assert [r.status_code for r in no_csrf] == [403, 403]
    assert anonymous.post(reprocess_url(document)).status_code == 401
    assert anonymous.put(classification_url(document), json=body).status_code == 401
    assert client.post(reprocess_url(document), headers=other).status_code == 404
    assert client.put(classification_url(document), json=body, headers=other).status_code == 404
    assert client.post(f"/api/documents/{uuid.uuid4()}/reprocess", headers=other).status_code == 404


# --- classification: DOC-11 ------------------------------------------------------------------


def test_manual_classification_is_stored_and_the_suggestion_is_kept(
    client, headers, process, uow_factory
):
    document = processed(client, headers, process, uow_factory)
    with uow_factory() as uow:  # the AI had suggested something else
        from dataclasses import replace

        current = uow.documents.get(uuid.UUID(document["id"]))
        uow.documents.update(
            replace(current, suggested_type="ATA_DEFESA", suggested_category="BANCA_MESTRADO"),
            current.version,
        )
        uow.commit()

    response = client.put(
        classification_url(document),
        json={"tipo": "CERTIFICADO", "categoria": "CURSO_EXTENSAO_CONCLUIDO"},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == document["id"]
    assert body["manual_type"] == "CERTIFICADO"
    assert body["manual_category"] == "CURSO_EXTENSAO_CONCLUIDO"
    assert body["suggested_type"] == "ATA_DEFESA"
    assert body["suggested_category"] == "BANCA_MESTRADO"
    assert body["version"] > document["version"]
    assert client.get(f"/api/documents/{document['id']}").json()["manual_type"] == "CERTIFICADO"


@pytest.mark.parametrize(
    ("body", "field"),
    [
        ({"tipo": "NAO_EXISTE", "categoria": "CURSO_CONCLUIDO"}, "tipo"),
        ({"tipo": "CERTIFICADO", "categoria": "NAO_EXISTE"}, "categoria"),
        ({"categoria": "CURSO_CONCLUIDO"}, "tipo"),
        ({"tipo": "CERTIFICADO"}, "categoria"),
    ],
)
def test_a_value_outside_the_enums_or_missing_is_422_on_that_field(
    client, headers, process, uow_factory, body, field
):
    document = processed(client, headers, process, uow_factory)

    response = client.put(classification_url(document), json=body, headers=headers)

    assert response.status_code == 422
    assert response.json()["detail"][0]["field"] == field
    assert client.get(f"/api/documents/{document['id']}").json()["manual_type"] is None


def test_classification_with_a_stale_expected_version_is_409(
    client, headers, process, uow_factory
):
    document = processed(client, headers, process, uow_factory)
    body = {"tipo": "CERTIFICADO", "categoria": "CURSO_CONCLUIDO"}

    stale = client.put(
        classification_url(document), json={**body, "expected_version": 99}, headers=headers
    )
    current = client.put(
        classification_url(document),
        json={**body, "expected_version": document["version"]},
        headers=headers,
    )

    assert stale.status_code == 409
    assert current.status_code == 200


def test_classification_on_a_closed_process_is_409(client, headers, process, uow_factory):
    document = processed(client, headers, process, uow_factory)
    close_process(client, headers, process, uow_factory)

    response = client.put(
        classification_url(document),
        json={"tipo": "CERTIFICADO", "categoria": "CURSO_CONCLUIDO"},
        headers=headers,
    )

    assert response.status_code == 409
