"""UNIT-01 (ADMIN manages academic units), UNIT-02 (archived unit cannot be selected), AUD-01."""

import uuid

import pytest

from app.application.use_cases.units import require_active_unit
from app.domain.entities.academic_unit import AcademicUnit, UnitKind
from app.domain.entities.audit import AuditAction
from app.domain.entities.user import Role
from app.domain.errors import ValidationFailed

CAMPUS = {"name": "Campus Tocantins/Cametá", "acronym": "CUNTINS", "kind": "CAMPUS"}


@pytest.fixture
def admin(act_as):
    return act_as("admin@ufpa.br", Role.ADMIN)


def test_admin_creates_unit_with_parent(client, admin):
    _, headers = admin
    campus = client.post("/api/units", json=CAMPUS, headers=headers).json()

    response = client.post(
        "/api/units",
        json={"name": "FASI", "acronym": "FASI", "kind": "FACULDADE", "parent_id": campus["id"]},
        headers=headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert {k: v for k, v in body.items() if k != "id"} == {
        "name": "FASI",
        "acronym": "FASI",
        "kind": "FACULDADE",
        "parent_id": campus["id"],
        "archived": False,
    }


def test_admin_edits_unit_and_only_changed_fields_are_audited(client, admin, uow_factory):
    actor, headers = admin
    unit = client.post("/api/units", json=CAMPUS, headers=headers).json()

    response = client.put(
        f"/api/units/{unit['id']}", json={**CAMPUS, "acronym": "CAMETA"}, headers=headers
    )

    assert response.status_code == 200
    assert response.json()["acronym"] == "CAMETA"
    with uow_factory() as uow:
        events = uow.audit.list_for("academic_unit", unit["id"])
    assert [e.action for e in events] == [AuditAction.CREATE, AuditAction.UPDATE]
    assert events[1].user_id == actor.id
    assert events[1].changes == {"acronym": {"before": "CUNTINS", "after": "CAMETA"}}


def test_admin_archives_unit_and_listing_shows_it_archived(client, admin, uow_factory):
    _, headers = admin
    unit = client.post("/api/units", json=CAMPUS, headers=headers).json()

    response = client.post(f"/api/units/{unit['id']}/archive", headers=headers)

    assert response.status_code == 200
    assert response.json()["archived"] is True
    assert [u["archived"] for u in client.get("/api/units").json()] == [True]
    with uow_factory() as uow:
        events = uow.audit.list_for("academic_unit", unit["id"])
    assert events[-1].action is AuditAction.ARCHIVE
    assert events[-1].changes == {"archived": {"before": False, "after": True}}


@pytest.mark.parametrize(
    ("payload", "field"),
    [
        ({**CAMPUS, "name": " "}, "name"),
        ({**CAMPUS, "acronym": ""}, "acronym"),
        ({**CAMPUS, "kind": "DEPARTAMENTO"}, "kind"),
        ({**CAMPUS, "parent_id": str(uuid.uuid4())}, "parent_id"),
    ],
    ids=["blank-name", "blank-acronym", "unknown-kind", "unknown-parent"],
)
def test_invalid_unit_returns_422_naming_the_field(client, admin, payload, field):
    _, headers = admin

    response = client.post("/api/units", json=payload, headers=headers)

    assert response.status_code == 422
    assert [error["field"] for error in response.json()["detail"]] == [field]


def test_unknown_unit_returns_404_on_edit_and_archive(client, admin):
    _, headers = admin
    missing = uuid.uuid4()

    assert client.put(f"/api/units/{missing}", json=CAMPUS, headers=headers).status_code == 404
    assert client.post(f"/api/units/{missing}/archive", headers=headers).status_code == 404


@pytest.mark.parametrize("role", [Role.SECRETARIA, Role.DOCENTE])
def test_non_admin_lists_but_cannot_change_units(client, act_as, uow_factory, role):
    unit = AcademicUnit(id=uuid.uuid4(), name="FASI", acronym="FASI", kind=UnitKind.FACULDADE)
    with uow_factory() as uow:
        uow.units.add(unit)
        uow.commit()
    _, headers = act_as("usuario@ufpa.br", role)

    listed = client.get("/api/units")
    created = client.post("/api/units", json=CAMPUS, headers=headers)
    edited = client.put(f"/api/units/{unit.id}", json=CAMPUS, headers=headers)
    archived = client.post(f"/api/units/{unit.id}/archive", headers=headers)

    assert listed.status_code == 200
    assert [u["acronym"] for u in listed.json()] == ["FASI"]
    assert (created.status_code, edited.status_code, archived.status_code) == (403, 403, 403)
    with uow_factory() as uow:
        assert uow.units.list() == [unit]


def test_archived_unit_cannot_be_selected(uow_factory):
    active = AcademicUnit(id=uuid.uuid4(), name="FASI", acronym="FASI", kind=UnitKind.FACULDADE)
    archived = AcademicUnit(
        id=uuid.uuid4(), name="Antiga", acronym="ANT", kind=UnitKind.FACULDADE, archived=True
    )
    with uow_factory() as uow:
        uow.units.add(active)
        uow.units.add(archived)
        uow.commit()

    with uow_factory() as uow:
        assert require_active_unit(uow, active.id) == active
        with pytest.raises(ValidationFailed) as exc:
            require_active_unit(uow, archived.id)
    assert exc.value.field == "unit_id"
