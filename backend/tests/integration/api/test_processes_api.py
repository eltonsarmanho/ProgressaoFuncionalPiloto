"""PROC-01..PROC-04, PROC-10, PROC-11, PROC-14, AUTH-08, AUTH-09, UNIT-02 through the API."""

import pytest
from sqlalchemy import text

from app.domain.entities.audit import AuditAction
from app.domain.entities.user import Role
from tests.integration.api.factories import (
    FASI_2022_2024,
    REQUERIMENTO_2024_2026,
    add_professor,
    process_payload,
)


@pytest.fixture
def fasi_professor(uow_factory, reference):
    return add_professor(uow_factory, reference["FASI"])


@pytest.fixture
def secretaria(act_as, reference):
    return act_as("sec.fasi@ufpa.br", Role.SECRETARIA, unit_ids=frozenset({reference["FASI"].id}))


def codes(body):
    return {alert["code"] for alert in body["alerts"]}


def test_created_process_persists_all_fields_with_id_and_rascunho(
    client, secretaria, fasi_professor
):
    _, headers = secretaria
    payload = process_payload(fasi_professor)

    created = client.post("/api/processes", json=payload, headers=headers)

    assert created.status_code == 201
    body = client.get(f"/api/processes/{created.json()['id']}").json()
    assert {k: body[k] for k in payload} == payload
    assert body["id"] == created.json()["id"]
    assert body["status"] == "RASCUNHO"
    assert body["version"] == 1


def test_process_creation_is_audited(client, secretaria, fasi_professor, uow_factory):
    actor, headers = secretaria

    created = client.post(
        "/api/processes", json=process_payload(fasi_professor), headers=headers
    ).json()

    with uow_factory() as uow:
        events = uow.audit.list_for("process", created["id"])
    assert [(e.action, e.user_id) for e in events] == [(AuditAction.CREATE, actor.id)]
    assert events[0].changes["target_level"] == {"before": None, "after": 1}
    assert events[0].changes["status"] == {"before": None, "after": "RASCUNHO"}


def test_proc10_fasi_case_has_24_months_and_no_alerts(client, secretaria, fasi_professor):
    _, headers = secretaria

    response = client.post(
        "/api/processes", json=process_payload(fasi_professor, FASI_2022_2024), headers=headers
    )

    assert response.status_code == 201
    body = response.json()
    assert body["interstice"] == {"months": 24, "days": 731}
    assert not [a for a in body["alerts"] if a["severity"] == "ERRO"]
    # Res. 4.644/2015 applied: under Lei 15.141/2025 "Adjunto" in class C would diverge
    assert codes(body) == set()


def test_proc11_requerimento_case_returns_exact_codes_and_keeps_values(
    client, secretaria, fasi_professor
):
    _, headers = secretaria
    payload = process_payload(fasi_professor, REQUERIMENTO_2024_2026)

    response = client.post("/api/processes", json=payload, headers=headers)

    assert response.status_code == 201
    body = response.json()
    assert codes(body) == {
        "MODALIDADE_INCOMPATIVEL",
        "CLASSE_INEXISTENTE_NA_ESTRUTURA",
        "DENOMINACAO_DIVERGENTE",
        "INTERSTICIO_NAO_CONCLUIDO",
        "INTERSTICIO_CRUZA_REESTRUTURACAO",
    }
    assert len(body["alerts"]) == 5
    assert body["interstice"] == {"months": 24, "days": 730}
    severities = {a["code"]: a["severity"] for a in body["alerts"]}
    assert severities == {
        "MODALIDADE_INCOMPATIVEL": "ALERTA",  # NMOV-02: a jump is an alert
        "CLASSE_INEXISTENTE_NA_ESTRUTURA": "ERRO",
        "DENOMINACAO_DIVERGENTE": "ALERTA",
        "INTERSTICIO_NAO_CONCLUIDO": "ALERTA",
        "INTERSTICIO_CRUZA_REESTRUTURACAO": "REQUER_ANALISE_NORMATIVA",
    }
    assert all(a["message"] and a["norm_reference"] for a in body["alerts"])
    modality = next(a for a in body["alerts"] if a["code"] == "MODALIDADE_INCOMPATIVEL")
    assert modality["message"] == (
        "A promoção informada não segue a sequência usual (último nível da classe atual "
        "para o primeiro nível da classe seguinte); confira a norma que fundamenta o salto."
    )
    cross = next(a for a in body["alerts"] if a["code"] == "INTERSTICIO_CRUZA_REESTRUTURACAO")
    assert "Lei 15.141/2025" in cross["norm_reference"]
    # PROC-03: values saved exactly as informed, despite the alerts
    stored = client.get(f"/api/processes/{body['id']}").json()
    assert {k: stored[k] for k in payload} == payload
    assert codes(stored) == codes(body)  # PROC-04: also verified on retrieval


REMOVED_FIELDS = ("notes", "resp_name", "resp_position", "resp_appointment", "resp_admin_unit")
LEGACY_VALUES = {
    "notes": "obs antiga",
    "resp_name": "Resp antigo",
    "resp_position": "Cargo antigo",
    "resp_appointment": "Portaria antiga",
    "resp_admin_unit": "Unidade antiga",
}


def legacy_row(engine, process_id):
    with engine.connect() as conn:
        row = conn.execute(
            text(f"SELECT {', '.join(REMOVED_FIELDS)} FROM functional_processes WHERE id = :id"),
            {"id": process_id},
        ).mappings().one()
    return dict(row)


# ENX-02, ENX-03, ENX-06
def test_a_process_without_the_removed_fields_saves_with_no_alert_and_no_such_keys(
    client, secretaria, fasi_professor
):
    _, headers = secretaria

    response = client.post(
        "/api/processes", json=process_payload(fasi_professor, FASI_2022_2024), headers=headers
    )

    assert response.status_code == 201
    assert response.json()["alerts"] == []
    read = client.get(f"/api/processes/{response.json()['id']}").json()
    for body in (response.json(), read):
        assert set(REMOVED_FIELDS).isdisjoint(body)


# ENX-04, ENX-05
def test_the_removed_fields_sent_by_an_old_client_are_ignored_and_not_stored(
    client, secretaria, fasi_professor, engine
):
    _, headers = secretaria
    payload = {**process_payload(fasi_professor, FASI_2022_2024), **LEGACY_VALUES}

    response = client.post("/api/processes", json=payload, headers=headers)

    assert response.status_code == 201
    assert set(REMOVED_FIELDS).isdisjoint(response.json())
    assert legacy_row(engine, response.json()["id"]) == dict.fromkeys(REMOVED_FIELDS)


# ENX-05, ENX-07: old values stay in the table, untouched by a new save and absent from the audit
def test_old_values_stay_in_the_columns_when_the_process_is_saved_again(
    client, secretaria, fasi_professor, engine, uow_factory
):
    _, headers = secretaria
    created = client.post(
        "/api/processes", json=process_payload(fasi_professor, FASI_2022_2024), headers=headers
    ).json()
    assignments = ", ".join(f"{f} = :{f}" for f in REMOVED_FIELDS)
    with engine.begin() as conn:
        conn.execute(
            text(f"UPDATE functional_processes SET {assignments} WHERE id = :id"),
            {**LEGACY_VALUES, "id": created["id"]},
        )

    edited = client.put(
        f"/api/processes/{created['id']}",
        json={
            **process_payload(fasi_professor, FASI_2022_2024),
            "target_level": 2,
            "expected_version": created["version"],
        },
        headers=headers,
    )

    assert edited.status_code == 200, edited.text
    assert set(REMOVED_FIELDS).isdisjoint(edited.json())
    assert legacy_row(engine, created["id"]) == LEGACY_VALUES
    with uow_factory() as uow:
        events = uow.audit.list_for("process", created["id"])
    assert events
    for event in events:  # the creation and the edition
        assert set(REMOVED_FIELDS).isdisjoint(event.changes)


def test_archived_unit_cannot_be_selected_for_new_process(
    client, act_as, reference, fasi_professor, uow_factory
):
    _, headers = act_as("admin@ufpa.br", Role.ADMIN)
    client.post(f"/api/units/{reference['IFCH'].id}/archive", headers=headers)

    response = client.post(
        "/api/processes",
        json=process_payload(fasi_professor, unit_id=str(reference["IFCH"].id)),
        headers=headers,
    )

    assert response.status_code == 422
    assert [error["field"] for error in response.json()["detail"]] == ["unit_id"]
    with uow_factory() as uow:
        assert uow.processes.list() == []


@pytest.fixture
def two_processes(client, act_as, reference, uow_factory):
    """One FASI process (Requerimento case) and one IFCH process (FASI case), by ADMIN."""
    fasi_prof = add_professor(uow_factory, reference["FASI"])
    ifch_prof = add_professor(uow_factory, reference["IFCH"], siape="7654321", name="João Ifch")
    _, headers = act_as("admin@ufpa.br", Role.ADMIN)
    fasi = client.post(
        "/api/processes",
        json=process_payload(fasi_prof, REQUERIMENTO_2024_2026),
        headers=headers,
    ).json()
    ifch = client.post(
        "/api/processes", json=process_payload(ifch_prof, FASI_2022_2024), headers=headers
    ).json()
    return {"fasi": fasi, "ifch": ifch, "fasi_prof": fasi_prof, "ifch_prof": ifch_prof}


def test_admin_lists_all_processes_with_alert_counts(client, two_processes):
    response = client.get("/api/processes")

    assert response.status_code == 200
    by_id = {item["id"]: item for item in response.json()}
    assert set(by_id) == {two_processes["fasi"]["id"], two_processes["ifch"]["id"]}
    fasi = by_id[two_processes["fasi"]["id"]]
    # NMOV-02: the promotion jump (MODALIDADE_INCOMPATIVEL) counts as ALERTA, not ERRO
    assert fasi["alert_counts"] == {"ERRO": 1, "ALERTA": 3, "REQUER_ANALISE_NORMATIVA": 1}
    assert fasi["status"] == "RASCUNHO"
    assert fasi["professor_id"] == str(two_processes["fasi_prof"].id)
    assert fasi["professor_name"] == "Maria Docente da Silva"
    assert fasi["modality"] == "PROMOCAO"
    assert (fasi["start_date"], fasi["end_date"]) == ("2024-11-23", "2026-11-23")
    assert fasi["interstice"] == {"months": 24, "days": 730}
    ifch = by_id[two_processes["ifch"]["id"]]
    assert ifch["alert_counts"] == {"ERRO": 0, "ALERTA": 0, "REQUER_ANALISE_NORMATIVA": 0}


def test_secretaria_sees_only_processes_of_its_units(client, act_as, reference, two_processes):
    act_as("sec.ifch@ufpa.br", Role.SECRETARIA, unit_ids=frozenset({reference["IFCH"].id}))

    listed = [item["id"] for item in client.get("/api/processes").json()]
    own = client.get(f"/api/processes/{two_processes['ifch']['id']}")
    other = client.get(f"/api/processes/{two_processes['fasi']['id']}")

    assert listed == [two_processes["ifch"]["id"]]
    assert own.status_code == 200
    assert other.status_code == 404


def test_docente_sees_only_processes_of_linked_professor(client, act_as, two_processes):
    act_as("docente@ufpa.br", Role.DOCENTE, professor_id=two_processes["fasi_prof"].id)

    listed = [item["id"] for item in client.get("/api/processes").json()]
    own = client.get(f"/api/processes/{two_processes['fasi']['id']}")
    other = client.get(f"/api/processes/{two_processes['ifch']['id']}")

    assert listed == [two_processes["fasi"]["id"]]
    assert own.status_code == 200
    assert other.status_code == 404
    assert other.json() == {"detail": "Processo não encontrado"}


def test_docente_without_linked_professor_sees_nothing(client, act_as, two_processes):
    act_as("docente@ufpa.br", Role.DOCENTE)

    assert client.get("/api/processes").json() == []
    assert client.get(f"/api/processes/{two_processes['fasi']['id']}").status_code == 404


def test_docente_creates_process_only_for_linked_professor(client, act_as, reference, uow_factory):
    own = add_professor(uow_factory, reference["FASI"])
    other = add_professor(uow_factory, reference["FASI"], siape="7654321", name="Outro Docente")
    _, headers = act_as("docente@ufpa.br", Role.DOCENTE, professor_id=own.id)

    mine = client.post("/api/processes", json=process_payload(own), headers=headers)
    theirs = client.post("/api/processes", json=process_payload(other), headers=headers)

    assert mine.status_code == 201
    assert theirs.status_code == 422
    assert [error["field"] for error in theirs.json()["detail"]] == ["professor_id"]


def test_secretaria_cannot_open_process_in_other_unit(
    client, act_as, reference, uow_factory, fasi_professor
):
    _, headers = act_as(
        "sec.fasi@ufpa.br", Role.SECRETARIA, unit_ids=frozenset({reference["FASI"].id})
    )

    response = client.post(
        "/api/processes",
        json=process_payload(fasi_professor, unit_id=str(reference["IFCH"].id)),
        headers=headers,
    )

    assert response.status_code == 403
