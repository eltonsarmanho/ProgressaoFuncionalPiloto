"""GP-DEL-03 to GP-DEL-07, GP-DEL-10 and the preview (GP-D7) through the API; the version in
the process summary (GP-D8)."""

import uuid

import pytest

from app.domain.entities.user import Role
from tests.integration.api.documents_support import (
    finish_processing,
    seed_document,
    stored_files,
    upload_one,
)
from tests.integration.api.factories import process_payload


@pytest.fixture
def as_user(make_client, make_user):
    """A user with a client of their own, logged in: (client, CSRF headers)."""
    from tests.integration.api.conftest import login

    def make(email, role, **kw):
        make_user(email, role=role, **kw)
        other = make_client()
        return other, {"X-CSRF-Token": login(other, email)}

    return make


@pytest.fixture
def secretaria(as_user, reference):
    """A SECRETARIA of FASI who is not the creator of the process."""
    return as_user("sec.fasi@ufpa.br", Role.SECRETARIA, unit_ids=frozenset({reference["FASI"].id}))


@pytest.fixture
def stranger(as_user, reference):
    """A SECRETARIA of another unit."""
    return as_user("sec.ifch@ufpa.br", Role.SECRETARIA, unit_ids=frozenset({reference["IFCH"].id}))


def url(process) -> str:
    return f"/api/processes/{process['id']}"


def test_delete_answers_204_and_every_route_of_the_process_becomes_404(
    client, headers, process, uow_factory
):
    seed_document(uow_factory, process, uow_factory_admin(uow_factory))

    response = client.delete(url(process), headers=headers)

    assert response.status_code == 204
    assert response.content == b""
    for route in ("", "/documents", "/activities", "/history", "/delete-preview"):
        assert client.get(url(process) + route).status_code == 404, route
    assert client.delete(url(process), headers=headers).status_code == 404
    assert [p["id"] for p in client.get("/api/processes").json()] == []


def uow_factory_admin(uow_factory):
    with uow_factory() as uow:
        return next(u for u in uow.users.list() if u.role is Role.ADMIN)


def test_the_files_of_the_documents_leave_the_disk(client, headers, process, uow_factory, tmp_path):
    document = upload_one(client, headers, process)
    finish_processing(uow_factory, document)
    assert len(stored_files(tmp_path)) == 1

    assert client.delete(url(process), headers=headers).status_code == 204

    assert stored_files(tmp_path) == []


def test_a_document_in_the_queue_blocks_with_409_and_the_code(
    client, headers, process, tmp_path
):
    upload_one(client, headers, process)

    response = client.delete(url(process), headers=headers)

    assert response.status_code == 409
    assert response.json()["code"] == "OPERACAO_EM_ANDAMENTO"
    assert client.get(url(process)).status_code == 200
    assert len(client.get(f"{url(process)}/documents").json()) == 1
    assert len(stored_files(tmp_path)) == 1


def test_a_reader_who_is_not_the_owner_gets_403_with_the_message(
    client, headers, process, secretaria
):
    other, other_headers = secretaria

    response = other.delete(url(process), headers=other_headers)

    assert response.status_code == 403
    assert "Apenas ADMIN ou o dono" in response.json()["detail"]
    assert client.get(url(process)).status_code == 200


def test_the_creator_secretaria_can_delete(secretaria, professor):
    client, headers = secretaria
    created = client.post("/api/processes", json=process_payload(professor), headers=headers)

    assert client.delete(url(created.json()), headers=headers).status_code == 204


def test_a_user_outside_the_unit_and_an_unknown_process_get_404(
    client, headers, process, stranger
):
    other, other_headers = stranger

    assert other.delete(url(process), headers=other_headers).status_code == 404
    assert client.delete(f"/api/processes/{uuid.uuid4()}", headers=headers).status_code == 404
    assert client.get(url(process)).status_code == 200


def test_delete_needs_a_session_and_the_csrf_token(client, make_client, headers, process):
    anonymous = make_client()

    assert client.delete(url(process)).status_code == 403
    assert anonymous.delete(url(process)).status_code == 401
    assert anonymous.get(f"{url(process)}/delete-preview").status_code == 401
    assert client.get(url(process)).status_code == 200


def test_the_preview_counts_what_the_deletion_removes(client, headers, process, uow_factory):
    admin = uow_factory_admin(uow_factory)
    seed_document(uow_factory, process, admin)
    seed_document(uow_factory, process, admin)

    response = client.get(f"{url(process)}/delete-preview")

    assert response.status_code == 200
    assert response.json() == {"documents": 2, "activities": 0, "generated_documents": 0}


def test_the_preview_follows_the_permissions_of_the_deletion(
    client, headers, process, secretaria, stranger
):
    reader, stranger_client = secretaria[0], stranger[0]

    assert reader.get(f"{url(process)}/delete-preview").status_code == 403
    assert stranger_client.get(f"{url(process)}/delete-preview").status_code == 404
    assert client.get(f"/api/processes/{uuid.uuid4()}/delete-preview").status_code == 404


def test_the_process_summary_carries_the_version_for_the_status_change(client, process):
    [summary] = client.get("/api/processes").json()

    assert summary["version"] == process["version"] == 1
