"""AUTH-10 (user creation by ADMIN) and AUD-01 (audit event on creation)."""

import uuid

import pytest

from app.domain.entities.academic_unit import AcademicUnit, UnitKind
from app.domain.entities.audit import AuditAction
from app.domain.entities.user import Role
from tests.integration.api.conftest import login

ADMIN = "admin@ufpa.br"
NEW_USER = {
    "email": "secretaria@ufpa.br",
    "name": "Secretaria FASI",
    "role": "SECRETARIA",
    "password": "senha-com-10",
}


@pytest.fixture
def admin(client, make_user):
    user = make_user(ADMIN, role=Role.ADMIN, name="Admin")
    csrf = login(client, ADMIN)
    return user, {"X-CSRF-Token": csrf}


def test_admin_creates_user_and_audit_event_is_recorded(client, admin, uow_factory):
    actor, headers = admin

    response = client.post("/api/users", json=NEW_USER, headers=headers)

    assert response.status_code == 201
    body = response.json()
    fields = ("email", "name", "role", "professor_id", "unit_ids", "active")
    assert {k: body[k] for k in fields} == {
        "email": "secretaria@ufpa.br",
        "name": "Secretaria FASI",
        "role": "SECRETARIA",
        "professor_id": None,
        "unit_ids": [],
        "active": True,
    }
    assert "password" not in body and "password_hash" not in body
    with uow_factory() as uow:
        stored = uow.users.get_by_email("secretaria@ufpa.br")
        events = uow.audit.list_for("user", body["id"])
    assert stored.password_hash.startswith("$argon2id$")
    assert len(events) == 1
    event = events[0]
    assert event.action is AuditAction.CREATE
    assert event.user_id == actor.id
    assert event.entity == "user"
    assert event.occurred_at.utcoffset().total_seconds() == 0
    assert event.changes == {
        "active": {"before": None, "after": True},
        "email": {"before": None, "after": "secretaria@ufpa.br"},
        "name": {"before": None, "after": "Secretaria FASI"},
        "role": {"before": None, "after": "SECRETARIA"},
        "unit_ids": {"before": None, "after": []},
    }
    assert event.justification is None
    assert all("password" not in field for field in event.changes)


def test_admin_lists_users(client, admin):
    _, headers = admin
    client.post("/api/users", json=NEW_USER, headers=headers)

    response = client.get("/api/users")

    assert response.status_code == 200
    assert sorted(u["email"] for u in response.json()) == [ADMIN, "secretaria@ufpa.br"]


@pytest.mark.parametrize(
    ("override", "field"),
    [
        ({"password": "curta-9ch"}, "password"),
        ({"email": "sem-arroba"}, "email"),
        ({"name": "   "}, "name"),
        ({"role": "BANCA"}, "role"),
    ],
    ids=["short-password", "invalid-email", "blank-name", "unknown-role"],
)
def test_invalid_field_returns_422_naming_the_field(client, admin, override, field):
    _, headers = admin

    response = client.post("/api/users", json={**NEW_USER, **override}, headers=headers)

    assert response.status_code == 422
    assert [error["field"] for error in response.json()["detail"]] == [field]


def test_password_with_exactly_10_characters_is_accepted(client, admin):
    _, headers = admin

    response = client.post(
        "/api/users", json={**NEW_USER, "password": "1234567890"}, headers=headers
    )

    assert response.status_code == 201


@pytest.mark.parametrize("email", ["secretaria@ufpa.br", "SECRETARIA@ufpa.br"])
def test_duplicate_email_returns_422_on_email(client, admin, email):
    _, headers = admin
    assert client.post("/api/users", json=NEW_USER, headers=headers).status_code == 201

    response = client.post("/api/users", json={**NEW_USER, "email": email}, headers=headers)

    assert response.status_code == 422
    assert [error["field"] for error in response.json()["detail"]] == ["email"]


@pytest.mark.parametrize("role", [Role.SECRETARIA, Role.DOCENTE])
def test_non_admin_cannot_create_or_list_users(client, make_user, uow_factory, role):
    make_user("outro@ufpa.br", role=role)
    csrf = login(client, "outro@ufpa.br")

    created = client.post("/api/users", json=NEW_USER, headers={"X-CSRF-Token": csrf})
    listed = client.get("/api/users")

    assert created.status_code == 403
    assert listed.status_code == 403
    with uow_factory() as uow:
        assert uow.users.get_by_email("secretaria@ufpa.br") is None


def test_secretaria_is_created_linked_to_units(client, admin, uow_factory):
    _, headers = admin
    fasi = AcademicUnit(id=uuid.uuid4(), name="FASI", acronym="FASI", kind=UnitKind.FACULDADE)
    with uow_factory() as uow:
        uow.units.add(fasi)
        uow.commit()

    response = client.post(
        "/api/users", json={**NEW_USER, "unit_ids": [str(fasi.id)]}, headers=headers
    )

    assert response.status_code == 201
    assert response.json()["unit_ids"] == [str(fasi.id)]
    with uow_factory() as uow:
        assert uow.users.get_by_email(NEW_USER["email"]).unit_ids == frozenset({fasi.id})


def test_unknown_unit_returns_422_on_unit_ids(client, admin):
    _, headers = admin

    response = client.post(
        "/api/users", json={**NEW_USER, "unit_ids": [str(uuid.uuid4())]}, headers=headers
    )

    assert response.status_code == 422
    assert [error["field"] for error in response.json()["detail"]] == ["unit_ids"]
