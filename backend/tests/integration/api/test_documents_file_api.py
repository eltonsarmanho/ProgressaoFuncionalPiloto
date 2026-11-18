"""DOC-05, DOC-06, DOC-08, DOC-09, DOC-10 (T37): file, replace and delete routes."""

import uuid

import pytest

from app.domain.entities.user import Role
from app.domain.repositories.ports import ActivityEvidence
from app.infrastructure.storage.local_storage import LocalFileStorage
from tests.integration.api.documents_support import (
    files_of,
    finish_processing,
    pdf,
    seed_document,
    stored_files,
    upload,
    upload_one,
)
from tests.integration.api.test_documents_api import close_process
from tests.support import synthetic_docs as synth


def file_url(document):
    return f"/api/documents/{document['id']}/file"


def replace(client, headers, document, content, name="novo.pdf", mime="application/pdf", **form):
    return client.put(
        file_url(document), files={"file": (name, content, mime)}, data=form, headers=headers
    )


def create_linked_activity(client, headers, uow_factory, process, user, document_id):
    """A manual activity linked to the document; returns its JSON."""
    created = client.post(
        f"/api/processes/{process['id']}/activities",
        json={"title": "Banca", "group_number": 3, "item_number": 4, "event_date": "2023-05-10"},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    activity = created.json()
    with uow_factory() as uow:
        uow.evidences.add(
            ActivityEvidence(
                uuid.uuid4(), uuid.UUID(activity["id"]), document_id, 1, "trecho", user.id
            )
        )
        uow.commit()
    return activity


# --- GET file: DOC-05, DOC-08 ---------------------------------------------------------------


def test_download_returns_the_original_bytes_as_attachment_with_nosniff(
    client, headers, process
):
    content = pdf("original")
    document = upload(client, headers, process, ("declaração ç.pdf", content)).json()[0]["document"]

    response = client.get(f"{file_url(document)}?download=1")

    assert response.status_code == 200
    assert response.content == content
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"] == (
        "attachment; filename*=UTF-8''declara%C3%A7%C3%A3o%20%C3%A7.pdf"
    )
    assert response.headers["x-content-type-options"] == "nosniff"


def test_the_default_view_is_inline_for_a_pdf_with_nosniff_and_sandbox(client, headers, process):
    content = pdf("em-linha")
    document = upload(client, headers, process, ("laudo.pdf", content)).json()[0]["document"]

    response = client.get(file_url(document))

    assert response.status_code == 200
    assert response.content == content
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"] == "inline; filename*=UTF-8''laudo.pdf"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["content-security-policy"] == "sandbox"


@pytest.mark.parametrize(
    ("name", "content", "mime"),
    [
        ("banca.png", synth.png_with_text(), "image/png"),
        ("banca.jpg", synth.jpg_with_text(), "image/jpeg"),
    ],
)
def test_an_image_is_shown_inline_byte_for_byte(client, headers, process, name, content, mime):
    document = upload(client, headers, process, (name, content, mime)).json()[0]["document"]

    response = client.get(file_url(document))

    assert response.status_code == 200
    assert response.content == content
    assert response.headers["content-type"] == mime
    assert response.headers["content-security-policy"] == "sandbox"
    assert response.headers["x-content-type-options"] == "nosniff"


def test_only_pdf_and_images_are_shown_inline_but_any_stored_file_can_be_downloaded(
    client, admin, process, uow_factory, tmp_path
):
    user, _ = admin
    internal = LocalFileStorage(tmp_path / "storage").save(
        uuid.UUID(process["id"]), ".pdf", b"conteudo qualquer"
    )
    document = seed_document(
        uow_factory, process, user, internal_name=internal, mime="application/zip"
    )
    url = f"/api/documents/{document.id}/file"

    refused = client.get(url)
    downloaded = client.get(f"{url}?download=1")

    assert refused.status_code == 422
    assert refused.json()["detail"][0]["field"] == "visualizar"
    assert downloaded.status_code == 200
    assert downloaded.content == b"conteudo qualquer"
    assert downloaded.headers["x-content-type-options"] == "nosniff"
    assert downloaded.headers["content-disposition"].startswith("attachment;")


def test_a_document_whose_file_is_gone_is_404(client, admin, process, uow_factory):
    user, _ = admin
    document = seed_document(uow_factory, process, user)  # row without a stored file

    assert client.get(f"/api/documents/{document.id}/file").status_code == 404


def test_the_file_needs_a_session_and_access_to_the_process(
    client, make_client, act_as, headers, process, reference
):
    document = upload_one(client, headers, process, "privado")
    anonymous = make_client()
    act_as("fora@ufpa.br", Role.SECRETARIA, unit_ids=frozenset({reference["IFCH"].id}))

    assert anonymous.get(file_url(document)).status_code == 401
    assert client.get(file_url(document)).status_code == 404
    assert client.get(f"/api/documents/{uuid.uuid4()}/file").status_code == 404


# --- PUT file: DOC-09 -----------------------------------------------------------------------


def test_replace_keeps_the_id_swaps_the_file_and_restarts_the_processing(
    client, headers, process, uow_factory, tmp_path
):
    document = upload_one(client, headers, process, "antigo")
    finish_processing(uow_factory, document)
    new = pdf("novo")
    before = client.get(f"/api/documents/{document['id']}").json()
    assert before["status"] == "PROCESSADO"

    response = replace(
        client, headers, document, new, name="substituto.pdf",
        expected_version=str(before["version"]),
    )  # fmt: skip

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == document["id"]
    assert body["original_name"] == "substituto.pdf"
    assert body["status"] == "PENDENTE"
    assert body["sha256"] != document["sha256"]
    assert body["version"] > before["version"]
    [only] = stored_files(tmp_path)
    assert only.read_bytes() == new
    assert client.get(f"{file_url(document)}?download=1").content == new


def test_replace_with_an_invalid_file_is_422_on_arquivo_with_the_code_and_keeps_the_old_file(
    client, headers, process, uow_factory, tmp_path
):
    document = upload_one(client, headers, process, "mantido")
    old = stored_files(tmp_path)[0].read_bytes()
    finish_processing(uow_factory, document)

    response = replace(client, headers, document, b"not a pdf at all", name="x.pdf")

    assert response.status_code == 422
    detail = response.json()["detail"][0]
    assert (detail["field"], detail["code"]) == ("arquivo", "ASSINATURA_DIVERGENTE")
    [only] = stored_files(tmp_path)
    assert only.read_bytes() == old


def test_replace_with_a_file_already_in_the_process_is_409_with_the_existing_id(
    client, headers, process, uow_factory
):
    first = upload_one(client, headers, process, "primeiro")
    second = upload_one(client, headers, process, "segundo")
    finish_processing(uow_factory, second)

    response = replace(client, headers, second, pdf("primeiro"), name="copia.pdf")

    assert response.status_code == 409
    assert response.json()["existing_document_id"] == first["id"]


def test_replace_while_the_document_is_queued_is_409(client, headers, process):
    document = upload_one(client, headers, process, "na-fila")  # PENDENTE: still in the queue

    response = replace(client, headers, document, pdf("outro"))

    assert response.status_code == 409


def test_replace_with_a_stale_expected_version_is_409_and_changes_nothing(
    client, headers, process, uow_factory, tmp_path
):
    document = upload_one(client, headers, process, "versao")
    old = stored_files(tmp_path)[0].read_bytes()
    finish_processing(uow_factory, document)

    response = replace(client, headers, document, pdf("novo-v"), expected_version="99")

    assert response.status_code == 409
    assert stored_files(tmp_path)[0].read_bytes() == old


@pytest.mark.parametrize("final", ["CONCLUIDO", "ARQUIVADO"])
def test_replace_and_delete_on_a_closed_process_are_409(
    client, headers, process, uow_factory, final
):
    document = upload_one(client, headers, process, f"fechado-{final}")
    finish_processing(uow_factory, document)
    close_process(client, headers, process, final)

    assert replace(client, headers, document, pdf("x")).status_code == 409
    deleted = client.delete(f"/api/documents/{document['id']}?justificativa=x", headers=headers)
    assert deleted.status_code == 409


def test_replace_needs_the_csrf_token_and_access(
    client, act_as, headers, process, reference, uow_factory
):
    document = upload_one(client, headers, process, "protegido")
    finish_processing(uow_factory, document)

    no_csrf = client.put(file_url(document), files=files_of(("n.pdf", pdf("n"))))
    _, other = act_as("fora@ufpa.br", Role.SECRETARIA, unit_ids=frozenset({reference["IFCH"].id}))
    outsider = replace(client, other, document, pdf("n2"))

    assert no_csrf.status_code == 403
    assert outsider.status_code == 404


# --- DELETE: DOC-10 -------------------------------------------------------------------------


def test_delete_is_204_removes_the_file_and_the_links_and_keeps_the_activity(
    client, admin, headers, process, uow_factory, tmp_path
):
    user, _ = admin
    document = upload_one(client, headers, process, "excluir")
    activity = create_linked_activity(
        client, headers, uow_factory, process, user, uuid.UUID(document["id"])
    )

    response = client.delete(
        f"/api/documents/{document['id']}?justificativa=Enviado por engano", headers=headers
    )

    assert response.status_code == 204
    assert response.content == b""
    assert stored_files(tmp_path) == []
    assert client.get(f"/api/documents/{document['id']}").status_code == 404
    assert client.get(f"/api/processes/{process['id']}/documents").json() == []
    assert client.get(f"/api/activities/{activity['id']}").status_code == 200
    with uow_factory() as uow:
        assert uow.evidences.list_for_activity(uuid.UUID(activity["id"])) == []


@pytest.mark.parametrize("query", ["", "?justificativa=", "?justificativa=%20%20"])
def test_delete_without_a_justification_is_204_and_removes_the_document(
    client, headers, process, tmp_path, query
):
    """UIM-04: no justification needed; the file and the record are gone."""
    document = upload_one(client, headers, process, "sem-justificativa")

    response = client.delete(f"/api/documents/{document['id']}{query}", headers=headers)

    assert response.status_code == 204
    assert stored_files(tmp_path) == []
    assert client.get(f"/api/documents/{document['id']}").status_code == 404


def test_delete_needs_the_csrf_token_and_access(client, act_as, headers, process, reference):
    document = upload_one(client, headers, process, "intocavel")
    url = f"/api/documents/{document['id']}?justificativa=x"

    no_csrf = client.delete(url)
    _, other = act_as("fora@ufpa.br", Role.SECRETARIA, unit_ids=frozenset({reference["IFCH"].id}))
    outsider = client.delete(url, headers=other)

    assert no_csrf.status_code == 403
    assert outsider.status_code == 404
