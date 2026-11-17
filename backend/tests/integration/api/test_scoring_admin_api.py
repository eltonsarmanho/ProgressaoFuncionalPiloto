"""ADM-01..ADM-11: scoring table administration routes (ADMIN writes, everyone reads)."""

import uuid

import pytest

from app.domain.entities.audit import AuditAction
from app.domain.entities.user import Role
from tests.integration.api.factories import add_professor, process_payload

FASI_NAME = "Tabela de Pontuação da FASI"
REFERENCE = "Res. 7.000/2026"
CSV_HEADER = "grupo,item,descricao,unidade,modo,pontos,horas_por_bloco,limite"
CSV_VALID = f"{CSV_HEADER}\n2,7,Orientação nova,por aluno,POR_UNIDADE,12.5,,30\n"


@pytest.fixture
def admin(act_as, scoring_tables):
    return act_as("admin@ufpa.br", Role.ADMIN)


def fasi(client):
    return next(t for t in client.get("/api/scoring-tables").json() if t["name"] == FASI_NAME)


def post_version(client, headers, table, **kw):
    body = {
        "source_version_id": table["versions"][-1]["id"],
        "valid_from": "2026-03-01",
        "norm_reference": REFERENCE,
        **kw,
    }
    return client.post(f"/api/scoring-tables/{table['id']}/versions", json=body, headers=headers)


def upload(client, headers, table, content=CSV_VALID, **data):
    data = {"valid_from": "2026-03-01", "norm_reference": REFERENCE, **data}
    return client.post(
        f"/api/scoring-tables/{table['id']}/versions/import",
        files={"file": ("criterios.csv", content, "text/csv")},
        data=data,
        headers=headers,
    )


def put_criterion(client, headers, version_id, group=2, item=7, **body):
    body = {"change_reference": REFERENCE, "changes": {"unit_points": "12.5"}, **body}
    return client.put(
        f"/api/scoring-versions/{version_id}/criteria/{group}/{item}", json=body, headers=headers
    )


def write_requests(client, headers, table, reference):
    """One request per write route, all with otherwise valid bodies."""
    version_id = table["versions"][0]["id"]
    return {
        "create": client.post(
            "/api/scoring-tables",
            json={
                "name": "X",
                "unit_ids": [],
                "valid_from": "2026-01-01",
                "norm_reference": REFERENCE,
            },
            headers=headers,
        ),
        "duplicate": client.post(
            f"/api/scoring-tables/{table['id']}/duplicate",
            json={"new_name": "Y"},
            headers=headers,
        ),
        "version": post_version(client, headers, table),
        "criterion": put_criterion(client, headers, version_id),
        "import": upload(client, headers, table),
        "units": client.put(
            f"/api/scoring-tables/{table['id']}/units",
            json={"unit_ids": [str(reference["IFCH"].id)]},
            headers=headers,
        ),
    }


def test_admin_creates_a_table_with_units_and_first_version(client, admin, reference, uow_factory):
    actor, headers = admin
    body = {
        "name": "Tabela do ICEN",
        "unit_ids": [str(reference["IFCH"].id)],
        "valid_from": "2026-01-01",
        "valid_to": None,
        "norm_reference": REFERENCE,
        "version_name": "Primeira",
    }

    response = client.post("/api/scoring-tables", json=body, headers=headers)

    assert response.status_code == 201
    created = response.json()
    assert created["name"] == "Tabela do ICEN"
    assert created["unit_ids"] == [str(reference["IFCH"].id)]
    [version] = created["versions"]
    assert (version["name"], version["valid_from"], version["valid_to"]) == (
        "Primeira",
        "2026-01-01",
        None,
    )
    assert version["norm_reference"] == REFERENCE
    assert version["status"] == "PENDENTE_VALIDACAO"
    detail = client.get(f"/api/scoring-versions/{version['id']}").json()
    assert [g["number"] for g in detail["groups"]] == [1, 2, 3, 4, 5, 6, 7, 8]
    with uow_factory() as uow:
        [event] = uow.audit.list_for("scoring_table", created["id"])
    assert (event.action, event.user_id) == (AuditAction.CREATE, actor.id)


def test_create_with_a_repeated_name_is_422_on_name(client, admin):
    _, headers = admin
    body = {"name": FASI_NAME, "valid_from": "2026-01-01", "norm_reference": REFERENCE}

    response = client.post("/api/scoring-tables", json=body, headers=headers)

    assert response.status_code == 422
    assert response.json()["detail"][0]["field"] == "name"
    assert len(client.get("/api/scoring-tables").json()) == 2


def test_create_without_norm_reference_is_422_on_norm_reference(client, admin):
    _, headers = admin

    response = client.post(
        "/api/scoring-tables", json={"name": "Z", "valid_from": "2026-01-01"}, headers=headers
    )

    assert response.status_code == 422
    assert response.json()["detail"][0]["field"] == "norm_reference"


@pytest.mark.parametrize("role", [Role.SECRETARIA, Role.DOCENTE])
def test_every_write_route_is_403_for_non_admin_and_changes_nothing(
    client, act_as, scoring_tables, reference, role
):
    _, headers = act_as("outro@ufpa.br", role)
    table = fasi(client)

    responses = write_requests(client, headers, table, reference)

    assert {name: r.status_code for name, r in responses.items()} == dict.fromkeys(responses, 403)
    assert len(client.get("/api/scoring-tables").json()) == 2
    assert len(fasi(client)["versions"]) == 1


def test_every_route_is_401_without_a_session(client, scoring_tables):
    table_id = uuid.uuid4()
    for method, url in [
        ("post", "/api/scoring-tables"),
        ("post", f"/api/scoring-tables/{table_id}/duplicate"),
        ("post", f"/api/scoring-tables/{table_id}/versions"),
        ("put", f"/api/scoring-versions/{table_id}/criteria/2/7"),
        ("post", f"/api/scoring-tables/{table_id}/versions/import"),
        ("put", f"/api/scoring-tables/{table_id}/units"),
        ("get", f"/api/scoring-tables/{table_id}/history"),
    ]:
        assert getattr(client, method)(url).status_code == 401, url


def test_duplicate_creates_an_independent_table_with_the_latest_version(client, admin):
    _, headers = admin
    table = fasi(client)

    response = client.post(
        f"/api/scoring-tables/{table['id']}/duplicate",
        json={"new_name": "Cópia da FASI"},
        headers=headers,
    )

    assert response.status_code == 201
    copy = response.json()
    assert copy["id"] != table["id"]
    assert copy["name"] == "Cópia da FASI"
    [copy_version] = copy["versions"]
    assert copy_version["id"] != table["versions"][0]["id"]
    assert copy_version["norm_reference"] == table["versions"][0]["norm_reference"]
    edited = put_criterion(client, headers, copy_version["id"], changes={"unit_points": "77"})
    assert edited.status_code == 200
    original = client.get(f"/api/scoring-versions/{table['versions'][0]['id']}").json()
    original_item = original["groups"][1]["criteria"][6]
    assert (original_item["item_number"], original_item["unit_points"]) == (7, "10.00")


def test_duplicate_name_clash_is_422_and_unknown_table_is_404(client, admin):
    _, headers = admin
    table = fasi(client)

    clash = client.post(
        f"/api/scoring-tables/{table['id']}/duplicate",
        json={"new_name": FASI_NAME},
        headers=headers,
    )
    unknown = client.post(
        f"/api/scoring-tables/{uuid.uuid4()}/duplicate", json={"new_name": "N"}, headers=headers
    )

    assert (clash.status_code, clash.json()["detail"][0]["field"]) == (422, "name")
    assert unknown.status_code == 404


def test_new_version_copies_criteria_and_closes_the_open_one(client, admin):
    _, headers = admin
    table = fasi(client)

    response = post_version(client, headers, table, version_name="2026")

    assert response.status_code == 201
    created = response.json()
    assert (created["valid_from"], created["valid_to"], created["name"]) == (
        "2026-03-01",
        None,
        "2026",
    )
    assert [len(g["criteria"]) for g in created["groups"]] == [3, 16, 12, 7, 6, 14, 11, 66]
    old, new = fasi(client)["versions"]
    assert old["valid_to"] == "2026-02-28"
    assert new["id"] == created["id"]


def test_new_version_is_409_when_a_process_would_lose_its_chosen_version(
    client, admin, reference, uow_factory, scoring_tables
):
    _, headers = admin
    professor = add_professor(uow_factory, reference["FASI"])
    process = client.post("/api/processes", json=process_payload(professor), headers=headers).json()
    chosen = client.put(
        f"/api/processes/{process['id']}/scoring/table",
        json={"version_id": str(scoring_tables["FASI"].id)},
        headers=headers,
    )
    assert chosen.status_code == 200

    response = post_version(client, headers, fasi(client), valid_from="2024-11-23")

    assert response.status_code == 409
    [only] = fasi(client)["versions"]
    assert only["valid_to"] is None


def test_overlapping_validity_is_409(client, admin):
    _, headers = admin
    table = fasi(client)
    assert post_version(client, headers, table).status_code == 201

    response = post_version(
        client, headers, fasi(client), valid_from="2023-01-01", valid_to="2023-12-31"
    )

    assert response.status_code == 409
    assert len(fasi(client)["versions"]) == 2


def test_new_version_without_norm_reference_is_422(client, admin):
    _, headers = admin
    table = fasi(client)
    body = {"source_version_id": table["versions"][0]["id"], "valid_from": "2026-03-01"}

    response = client.post(
        f"/api/scoring-tables/{table['id']}/versions", json=body, headers=headers
    )

    assert response.status_code == 422
    assert response.json()["detail"][0]["field"] == "norm_reference"


def test_criterion_change_is_audited_with_before_and_after(client, admin, uow_factory):
    actor, headers = admin
    table = client.post(
        f"/api/scoring-tables/{fasi(client)['id']}/duplicate",
        json={"new_name": "Cópia"},
        headers=headers,
    ).json()
    version_id = table["versions"][0]["id"]

    response = put_criterion(client, headers, version_id)

    assert response.status_code == 200
    assert (response.json()["item_number"], response.json()["unit_points"]) == (7, "12.50")
    with uow_factory() as uow:
        [event] = [
            e
            for e in uow.audit.list_for("scoring_version", version_id)
            if e.action is AuditAction.UPDATE
        ]
    assert event.user_id == actor.id
    assert event.justification == REFERENCE
    assert event.changes == {"criteria.2.7.unit_points": {"before": "10", "after": "12.5"}}


def test_criterion_change_without_reference_is_422(client, admin):
    _, headers = admin
    version_id = fasi(client)["versions"][0]["id"]

    response = put_criterion(client, headers, version_id, change_reference=" ")

    assert response.status_code == 422
    assert response.json()["detail"][0]["field"] == "change_reference"


def test_criterion_of_a_version_in_use_is_409_asking_for_a_new_version(
    client, admin, reference, uow_factory, scoring_tables
):
    _, headers = admin
    professor = add_professor(uow_factory, reference["FASI"])
    process = client.post("/api/processes", json=process_payload(professor), headers=headers).json()
    client.put(
        f"/api/processes/{process['id']}/scoring/table",
        json={"version_id": str(scoring_tables["FASI"].id)},
        headers=headers,
    )

    response = put_criterion(client, headers, str(scoring_tables["FASI"].id))

    assert response.status_code == 409
    assert "nova versão" in response.json()["detail"]


def test_unknown_criterion_is_404(client, admin):
    _, headers = admin
    version_id = fasi(client)["versions"][0]["id"]

    assert put_criterion(client, headers, version_id, item=999).status_code == 404


def test_csv_import_creates_the_new_version_with_every_row(client, admin):
    _, headers = admin
    table = fasi(client)

    response = upload(client, headers, table, valid_to="", status="OFICIAL")

    assert response.status_code == 201
    created = response.json()
    assert (created["valid_from"], created["valid_to"], created["status"]) == (
        "2026-03-01",
        None,
        "OFICIAL",
    )
    assert created["norm_reference"] == REFERENCE
    assert [len(g["criteria"]) for g in created["groups"]] == [0, 1, 0, 0, 0, 0, 0, 0]
    item = created["groups"][1]["criteria"][0]
    assert (item["description"], item["unit_points"], item["max_points"]) == (
        "Orientação nova",
        "12.50",
        "30.00",
    )
    assert fasi(client)["versions"][0]["valid_to"] == "2026-02-28"


def test_csv_with_bom_is_accepted(client, admin):
    _, headers = admin

    response = upload(client, headers, fasi(client), content=("﻿" + CSV_VALID).encode())

    assert response.status_code == 201


def test_csv_with_invalid_rows_is_422_listing_every_line_and_field_and_creates_nothing(
    client, admin
):
    _, headers = admin
    bad = (
        f"{CSV_HEADER}\n9,1,Ok,x,POR_UNIDADE,1,,\n"
        "2,8,Ok,x,INEXISTENTE,1,,\n2,9,Ok,x,POR_UNIDADE,a,,\n"
    )

    response = upload(client, headers, fasi(client), content=bad)

    assert response.status_code == 422
    assert [(e["field"], e["message"].split(":")[0]) for e in response.json()["detail"]] == [
        ("file", "linha 2, campo grupo"),
        ("file", "linha 3, campo modo"),
        ("file", "linha 4, campo pontos"),
    ]
    [only] = fasi(client)["versions"]
    assert only["valid_to"] is None


def test_csv_that_is_not_utf8_or_missing_is_422_on_file(client, admin):
    _, headers = admin
    table = fasi(client)

    not_utf8 = upload(client, headers, table, content="descrição".encode("latin-1"))
    missing = client.post(
        f"/api/scoring-tables/{table['id']}/versions/import",
        data={"valid_from": "2026-03-01", "norm_reference": REFERENCE},
        headers=headers,
    )

    assert (not_utf8.status_code, not_utf8.json()["detail"][0]["field"]) == (422, "file")
    assert (missing.status_code, missing.json()["detail"][0]["field"]) == (422, "file")
    assert len(fasi(client)["versions"]) == 1


def test_csv_import_without_norm_reference_is_422_and_unknown_table_404(client, admin):
    _, headers = admin
    table = fasi(client)

    no_reference = upload(client, headers, table, norm_reference=" ")
    unknown = upload(client, headers, {"id": str(uuid.uuid4())})

    assert (no_reference.status_code, no_reference.json()["detail"][0]["field"]) == (
        422,
        "norm_reference",
    )
    assert unknown.status_code == 404


def test_units_are_replaced_and_audited(client, admin, reference, uow_factory):
    actor, headers = admin
    table = fasi(client)

    response = client.put(
        f"/api/scoring-tables/{table['id']}/units",
        json={"unit_ids": [str(reference["FASI"].id), str(reference["IFCH"].id)]},
        headers=headers,
    )

    assert response.status_code == 200
    assert set(response.json()["unit_ids"]) == {
        str(reference["FASI"].id),
        str(reference["IFCH"].id),
    }
    assert set(fasi(client)["unit_ids"]) == set(response.json()["unit_ids"])
    with uow_factory() as uow:
        [event] = uow.audit.list_for("scoring_table", table["id"])
    assert (event.action, event.user_id) == (AuditAction.UPDATE, actor.id)
    assert event.changes["unit_ids"]["before"] == [str(reference["FASI"].id)]


def test_units_unknown_unit_is_422_and_unknown_table_404(client, admin):
    _, headers = admin
    table = fasi(client)

    bad_unit = client.put(
        f"/api/scoring-tables/{table['id']}/units",
        json={"unit_ids": [str(uuid.uuid4())]},
        headers=headers,
    )
    unknown = client.put(
        f"/api/scoring-tables/{uuid.uuid4()}/units", json={"unit_ids": []}, headers=headers
    )

    assert (bad_unit.status_code, bad_unit.json()["detail"][0]["field"]) == (422, "unit_ids")
    assert unknown.status_code == 404


def test_history_lists_versions_and_audit_events_chronologically_for_every_role(
    client, admin, act_as, clock
):
    _, headers = admin
    table = fasi(client)
    assert post_version(client, headers, table).status_code == 201
    assert put_criterion(client, headers, table["versions"][0]["id"]).status_code == 409
    docente_headers = act_as("docente@ufpa.br", Role.DOCENTE)[1]
    assert docente_headers

    response = client.get(f"/api/scoring-tables/{table['id']}/history")

    assert response.status_code == 200
    history = response.json()
    assert [(v["valid_from"], v["valid_to"], v["status"]) for v in history["versions"]] == [
        ("2022-11-23", "2026-02-28", "PENDENTE_VALIDACAO"),
        ("2026-03-01", None, "PENDENTE_VALIDACAO"),
    ]
    assert all(v["norm_reference"] for v in history["versions"])
    events = history["events"]
    assert [(e["entity"], e["action"]) for e in events] == [
        ("scoring_version", "UPDATE"),
        ("scoring_version", "CREATE"),
    ]
    assert events[0]["changes"] == {"valid_to": {"before": None, "after": "2026-02-28"}}
    assert events[1]["justification"] == REFERENCE
    assert events[0]["id"] < events[1]["id"]


def test_history_of_a_new_table_includes_the_table_creation_event(client, admin):
    _, headers = admin
    created = client.post(
        "/api/scoring-tables",
        json={"name": "Nova", "valid_from": "2026-01-01", "norm_reference": REFERENCE},
        headers=headers,
    ).json()

    history = client.get(f"/api/scoring-tables/{created['id']}/history").json()

    assert [(e["entity"], e["action"]) for e in history["events"]] == [
        ("scoring_table", "CREATE"),
        ("scoring_version", "CREATE"),
    ]
    assert client.get(f"/api/scoring-tables/{uuid.uuid4()}/history").status_code == 404


def test_superseded_version_stays_read_only(client, admin):
    _, headers = admin
    table = fasi(client)
    assert post_version(client, headers, table).status_code == 201

    response = put_criterion(client, headers, table["versions"][0]["id"])

    assert response.status_code == 409
    assert "somente leitura" in response.json()["detail"]
