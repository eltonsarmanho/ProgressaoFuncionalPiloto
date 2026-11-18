"""AUD-04: application logs carry only identifiers, never the professor's name or SIAPE."""

import logging

import pytest

from app.core.logging import ACCESS_LOGGER
from app.domain.entities.user import Role
from tests.integration.api.factories import FASI_2022_2024

NAME = "Raimunda Pessoal Identificável"
SIAPE = "9876543"


@pytest.fixture
def admin(act_as, reference):
    return act_as("admin@ufpa.br", Role.ADMIN)


def _record_text(record: logging.LogRecord) -> str:
    return " ".join([record.getMessage(), *(str(v) for v in vars(record).values())])


def test_full_flow_logs_contain_no_name_or_siape(client, admin, reference, caplog):
    _, headers = admin
    caplog.set_level(logging.INFO)  # production level for every logger

    professor_body = {
        "full_name": NAME,
        "siape": SIAPE,
        "titration": "DOUTORADO",
        "position": "Professor do Magistério Superior",
        "career": "MAGISTERIO_SUPERIOR",
        "unit_id": str(reference["FASI"].id),
        "faculty": "FASI",
        "campus": "Cametá",
        "work_regime": "DE",
    }
    professor = client.post("/api/professors", json=professor_body, headers=headers)
    assert professor.status_code == 201
    payload = {
        "professor_id": professor.json()["id"],
        "unit_id": str(reference["FASI"].id),
        **FASI_2022_2024,
    }
    process = client.post("/api/processes", json=payload, headers=headers)
    assert process.status_code == 201
    process_id = process.json()["id"]
    client.get(f"/api/processes/{process_id}")
    client.get("/api/processes")
    client.put(
        f"/api/processes/{process_id}",
        json={**FASI_2022_2024, "expected_version": 1, "notes": "Revisado"},
        headers=headers,
    )
    client.get(f"/api/processes/{process_id}/history")
    duplicate = client.post("/api/professors", json=professor_body, headers=headers)
    assert duplicate.status_code == 409  # failure paths must not leak either

    access = [r for r in caplog.records if r.name == ACCESS_LOGGER]
    assert len(access) >= 7
    leaked = [r for r in caplog.records if NAME in _record_text(r) or SIAPE in _record_text(r)]
    assert leaked == []


def test_access_log_records_method_route_template_status_duration_and_user(
    client, admin, reference, caplog
):
    actor, headers = admin
    caplog.set_level(logging.INFO, logger=ACCESS_LOGGER)

    client.post(f"/api/units/{reference['IFCH'].id}/archive", headers=headers)

    record = [r for r in caplog.records if r.name == ACCESS_LOGGER][-1]
    assert record.method == "POST"
    assert record.route == "/api/units/{unit_id}/archive"
    assert record.status == 200
    assert isinstance(record.duration_ms, float) and record.duration_ms >= 0
    assert record.user_id == str(actor.id)
    assert str(reference["IFCH"].id) not in record.getMessage()


def test_access_log_of_unauthenticated_request_has_no_user(client, caplog):
    caplog.set_level(logging.INFO, logger=ACCESS_LOGGER)

    client.get("/api/processes")

    record = [r for r in caplog.records if r.name == ACCESS_LOGGER][-1]
    assert (record.method, record.status, record.user_id) == ("GET", 401, None)
