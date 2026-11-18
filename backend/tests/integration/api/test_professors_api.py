"""DOC-01..DOC-05, UNIT-02 for professors, and read scoping (AUTH-08/09 style 404)."""

import uuid

import pytest

from app.domain.entities.audit import AuditAction
from app.domain.entities.user import Role


def professor_payload(units, **overrides):
    data = {
        "full_name": "Maria Docente da Silva",
        "siape": "1234567",
        "titration": "DOUTORADO",
        "position": "Professor do Magistério Superior",
        "career": "MAGISTERIO_SUPERIOR",
        "unit_id": str(units["FASI"].id),
        "faculty": "Faculdade de Sistemas de Informação",
        "campus": "Campus Universitário do Tocantins/Cametá",
        "work_regime": "DE",
    }
    data.update(overrides)
    return data


@pytest.fixture
def secretaria(act_as, reference):
    return act_as("sec.fasi@ufpa.br", Role.SECRETARIA, unit_ids=frozenset({reference["FASI"].id}))


@pytest.fixture
def admin(act_as, reference):
    return act_as("admin@ufpa.br", Role.ADMIN)


def test_professor_is_persisted_with_all_functional_fields(client, reference, secretaria):
    _, headers = secretaria
    payload = professor_payload(reference)

    created = client.post("/api/professors", json=payload, headers=headers)

    assert created.status_code == 201
    reopened = client.get(f"/api/professors/{created.json()['id']}")
    assert reopened.status_code == 200
    body = reopened.json()
    assert {k: body[k] for k in payload} == payload
    assert body["archived"] is False
    assert body["version"] == 1


@pytest.mark.parametrize("siape", ["123456", "12345678", "12345a7", "", " 123456"])
def test_siape_without_exactly_7_digits_returns_422_on_siape(client, reference, secretaria, siape):
    _, headers = secretaria

    response = client.post(
        "/api/professors", json=professor_payload(reference, siape=siape), headers=headers
    )

    assert response.status_code == 422
    assert [error["field"] for error in response.json()["detail"]] == ["siape"]


def test_duplicate_siape_returns_409_without_duplicate(client, reference, secretaria, uow_factory):
    _, headers = secretaria
    payload = professor_payload(reference)
    assert client.post("/api/professors", json=payload, headers=headers).status_code == 201

    response = client.post(
        "/api/professors", json={**payload, "full_name": "Outra Pessoa"}, headers=headers
    )

    assert response.status_code == 409
    with uow_factory() as uow:
        assert [p.siape for p in uow.professors.list()] == ["1234567"]


@pytest.mark.parametrize(
    ("override", "field"),
    [({"titration": "POS_DOUTORADO"}, "titration"), ({"work_regime": "30H"}, "work_regime")],
)
def test_values_outside_enums_return_422(client, reference, secretaria, override, field):
    _, headers = secretaria

    response = client.post(
        "/api/professors", json=professor_payload(reference, **override), headers=headers
    )

    assert response.status_code == 422
    assert [error["field"] for error in response.json()["detail"]] == [field]


def test_every_allowed_titration_and_work_regime_is_accepted(client, reference, secretaria):
    _, headers = secretaria
    pairs = [
        ("GRADUACAO", "20H"),
        ("ESPECIALIZACAO", "40H"),
        ("MESTRADO", "DE"),
        ("DOUTORADO", "DE"),
    ]

    statuses = [
        client.post(
            "/api/professors",
            json=professor_payload(reference, siape=f"100000{i}", titration=t, work_regime=r),
            headers=headers,
        ).status_code
        for i, (t, r) in enumerate(pairs)
    ]

    assert statuses == [201, 201, 201, 201]


def test_editing_records_audit_event_with_changed_fields_only(
    client, reference, secretaria, uow_factory
):
    actor, headers = secretaria
    payload = professor_payload(reference, work_regime="40H")
    created = client.post("/api/professors", json=payload, headers=headers).json()

    response = client.put(
        f"/api/professors/{created['id']}",
        json={**payload, "work_regime": "DE", "titration": "MESTRADO", "expected_version": 1},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["version"] == 2
    with uow_factory() as uow:
        events = uow.audit.list_for("professor", created["id"])
    assert [e.action for e in events] == [AuditAction.CREATE, AuditAction.UPDATE]
    update = events[1]
    assert update.user_id == actor.id
    assert update.entity_id == created["id"]
    assert update.changes == {
        "titration": {"before": "DOUTORADO", "after": "MESTRADO"},
        "work_regime": {"before": "40H", "after": "DE"},
    }


def test_editing_with_stale_version_returns_409(client, reference, secretaria):
    _, headers = secretaria
    payload = professor_payload(reference)
    created = client.post("/api/professors", json=payload, headers=headers).json()
    url = f"/api/professors/{created['id']}"
    first = client.put(url, json={**payload, "campus": "A", "expected_version": 1}, headers=headers)

    second = client.put(
        url, json={**payload, "campus": "B", "expected_version": 1}, headers=headers
    )

    assert first.status_code == 200
    assert second.status_code == 409
    assert client.get(url).json()["campus"] == "A"


def test_archived_unit_cannot_be_selected_for_new_professor(client, reference, admin, uow_factory):
    _, headers = admin
    assert client.post(f"/api/units/{reference['IFCH'].id}/archive", headers=headers).is_success

    response = client.post(
        "/api/professors",
        json=professor_payload(reference, unit_id=str(reference["IFCH"].id)),
        headers=headers,
    )

    assert response.status_code == 422
    assert [error["field"] for error in response.json()["detail"]] == ["unit_id"]
    with uow_factory() as uow:
        assert uow.professors.list() == []


def test_unknown_career_returns_422_on_career(client, reference, admin):
    _, headers = admin

    response = client.post(
        "/api/professors", json=professor_payload(reference, career="EBTT"), headers=headers
    )

    assert response.status_code == 422
    assert [error["field"] for error in response.json()["detail"]] == ["career"]


def test_docente_and_secretaria_outside_unit_cannot_create(client, reference, act_as):
    _, docente = act_as("docente@ufpa.br", Role.DOCENTE)
    by_docente = client.post("/api/professors", json=professor_payload(reference), headers=docente)
    _, other = act_as(
        "sec.ifch@ufpa.br", Role.SECRETARIA, unit_ids=frozenset({reference["IFCH"].id})
    )
    by_other_unit = client.post("/api/professors", json=professor_payload(reference), headers=other)

    assert by_docente.status_code == 403
    assert by_other_unit.status_code == 403


def test_reads_are_scoped_by_profile(client, reference, admin, act_as):
    _, headers = admin
    fasi = client.post("/api/professors", json=professor_payload(reference), headers=headers)
    ifch = client.post(
        "/api/professors",
        json=professor_payload(reference, siape="7654321", unit_id=str(reference["IFCH"].id)),
        headers=headers,
    )
    fasi_id, ifch_id = fasi.json()["id"], ifch.json()["id"]

    act_as("sec.ifch@ufpa.br", Role.SECRETARIA, unit_ids=frozenset({reference["IFCH"].id}))
    secretaria_view = (
        client.get(f"/api/professors/{fasi_id}").status_code,
        [p["id"] for p in client.get("/api/professors").json()],
    )
    act_as("docente@ufpa.br", Role.DOCENTE, professor_id=uuid.UUID(fasi_id))
    docente_view = (
        client.get(f"/api/professors/{ifch_id}").status_code,
        [p["id"] for p in client.get("/api/professors").json()],
    )

    assert secretaria_view == (404, [ifch_id])
    assert docente_view == (404, [fasi_id])


def test_archiving_professor_is_audited(client, reference, admin, uow_factory):
    actor, headers = admin
    created = client.post(
        "/api/professors", json=professor_payload(reference), headers=headers
    ).json()

    response = client.post(
        f"/api/professors/{created['id']}/archive", json={"expected_version": 1}, headers=headers
    )

    assert response.status_code == 200
    assert response.json()["archived"] is True
    with uow_factory() as uow:
        event = uow.audit.list_for("professor", created["id"])[-1]
    assert event.action is AuditAction.ARCHIVE
    assert event.user_id == actor.id
    assert event.changes == {"archived": {"before": False, "after": True}}
