"""ADM-01..ADM-11: scoring table administration routes (ADMIN writes, everyone reads)."""

import uuid

import pytest

from app.domain.entities.audit import AuditAction
from app.domain.entities.user import Role
from tests.integration.api.factories import add_professor, process_payload

OFFICIAL_NAME = "Tabela de Pontuação da UFPA"
REFERENCE = "Res. 7.000/2026"
CSV_HEADER = "grupo,item,descricao,unidade,modo,pontos,horas_por_bloco,limite"
CSV_VALID = f"{CSV_HEADER}\n2,7,Orientação nova,por aluno,POR_UNIDADE,12.5,,30\n"


@pytest.fixture
def admin(act_as, scoring_tables):
    return act_as("admin@ufpa.br", Role.ADMIN)


def official(client):
    return next(t for t in client.get("/api/scoring-tables").json() if t["name"] == OFFICIAL_NAME)


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
        "mark_in_use": client.put(
            f"/api/scoring-units/{reference['FASI'].id}/default-version",
            json={"version_id": version_id},
            headers=headers,
        ),
        "clear_in_use": client.delete(
            f"/api/scoring-units/{reference['FASI'].id}/default-version", headers=headers
        ),
        "archive": client.post(f"/api/scoring-tables/{table['id']}/archive", headers=headers),
        "unarchive": client.post(f"/api/scoring-tables/{table['id']}/unarchive", headers=headers),
        "delete_version": client.delete(f"/api/scoring-versions/{version_id}", headers=headers),
        "delete_table": client.delete(f"/api/scoring-tables/{table['id']}", headers=headers),
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
    body = {"name": OFFICIAL_NAME, "valid_from": "2026-01-01", "norm_reference": REFERENCE}

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
    table = official(client)

    responses = write_requests(client, headers, table, reference)

    assert {name: r.status_code for name, r in responses.items()} == dict.fromkeys(responses, 403)
    assert len(client.get("/api/scoring-tables").json()) == 2
    assert len(official(client)["versions"]) == 1


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
        ("put", f"/api/scoring-units/{table_id}/default-version"),
        ("delete", f"/api/scoring-units/{table_id}/default-version"),
        ("post", f"/api/scoring-tables/{table_id}/archive"),
        ("post", f"/api/scoring-tables/{table_id}/unarchive"),
        ("get", f"/api/scoring-versions/{table_id}/delete-preview"),
        ("get", f"/api/scoring-tables/{table_id}/delete-preview"),
        ("delete", f"/api/scoring-versions/{table_id}"),
        ("delete", f"/api/scoring-tables/{table_id}"),
    ]:
        assert getattr(client, method)(url).status_code == 401, url


def test_duplicate_creates_an_independent_table_with_the_latest_version(client, admin):
    _, headers = admin
    table = official(client)

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
    assert (original_item["item_number"], original_item["unit_points"]) == (7, "5.00")


def test_duplicate_name_clash_is_422_and_unknown_table_is_404(client, admin):
    _, headers = admin
    table = official(client)

    clash = client.post(
        f"/api/scoring-tables/{table['id']}/duplicate",
        json={"new_name": OFFICIAL_NAME},
        headers=headers,
    )
    unknown = client.post(
        f"/api/scoring-tables/{uuid.uuid4()}/duplicate", json={"new_name": "N"}, headers=headers
    )

    assert (clash.status_code, clash.json()["detail"][0]["field"]) == (422, "name")
    assert unknown.status_code == 404


def test_new_version_copies_criteria_and_closes_the_open_one(client, admin):
    _, headers = admin
    table = official(client)

    response = post_version(client, headers, table, version_name="2026")

    assert response.status_code == 201
    created = response.json()
    assert (created["valid_from"], created["valid_to"], created["name"]) == (
        "2026-03-01",
        None,
        "2026",
    )
    assert [len(g["criteria"]) for g in created["groups"]] == [2, 16, 9, 6, 5, 14, 11, 37]
    old, new = official(client)["versions"]
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
        json={"version_id": str(scoring_tables["OFICIAL"].id)},
        headers=headers,
    )
    assert chosen.status_code == 200

    response = post_version(client, headers, official(client), valid_from="2024-11-23")

    assert response.status_code == 409
    [only] = official(client)["versions"]
    assert only["valid_to"] is None


def test_overlapping_validity_is_409(client, admin):
    _, headers = admin
    table = official(client)
    assert post_version(client, headers, table).status_code == 201

    response = post_version(
        client, headers, official(client), valid_from="2023-01-01", valid_to="2023-12-31"
    )

    assert response.status_code == 409
    assert len(official(client)["versions"]) == 2


def test_new_version_without_norm_reference_is_422(client, admin):
    _, headers = admin
    table = official(client)
    body = {"source_version_id": table["versions"][0]["id"], "valid_from": "2026-03-01"}

    response = client.post(
        f"/api/scoring-tables/{table['id']}/versions", json=body, headers=headers
    )

    assert response.status_code == 422
    assert response.json()["detail"][0]["field"] == "norm_reference"


def test_criterion_change_is_audited_with_before_and_after(client, admin, uow_factory):
    actor, headers = admin
    table = client.post(
        f"/api/scoring-tables/{official(client)['id']}/duplicate",
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
    assert event.changes == {"criteria.2.7.unit_points": {"before": "5", "after": "12.5"}}


def test_criterion_change_without_reference_is_422(client, admin):
    _, headers = admin
    version_id = official(client)["versions"][0]["id"]

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
        json={"version_id": str(scoring_tables["OFICIAL"].id)},
        headers=headers,
    )

    response = put_criterion(client, headers, str(scoring_tables["OFICIAL"].id))

    assert response.status_code == 409
    assert "nova versão" in response.json()["detail"]


def test_unknown_criterion_is_404(client, admin):
    _, headers = admin
    version_id = official(client)["versions"][0]["id"]

    assert put_criterion(client, headers, version_id, item=999).status_code == 404


def test_csv_import_creates_the_new_version_with_every_row(client, admin):
    _, headers = admin
    table = official(client)

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
    assert official(client)["versions"][0]["valid_to"] == "2026-02-28"


def test_csv_with_bom_is_accepted(client, admin):
    _, headers = admin

    response = upload(client, headers, official(client), content=("﻿" + CSV_VALID).encode())

    assert response.status_code == 201


def test_csv_with_invalid_rows_is_422_listing_every_line_and_field_and_creates_nothing(
    client, admin
):
    _, headers = admin
    bad = (
        f"{CSV_HEADER}\n9,1,Ok,x,POR_UNIDADE,1,,\n"
        "2,8,Ok,x,INEXISTENTE,1,,\n2,9,Ok,x,POR_UNIDADE,a,,\n"
    )

    response = upload(client, headers, official(client), content=bad)

    assert response.status_code == 422
    assert [(e["field"], e["message"].split(":")[0]) for e in response.json()["detail"]] == [
        ("file", "linha 2, campo grupo"),
        ("file", "linha 3, campo modo"),
        ("file", "linha 4, campo pontos"),
    ]
    [only] = official(client)["versions"]
    assert only["valid_to"] is None


def test_csv_that_is_not_utf8_or_missing_is_422_on_file(client, admin):
    _, headers = admin
    table = official(client)

    not_utf8 = upload(client, headers, table, content="descrição".encode("latin-1"))
    missing = client.post(
        f"/api/scoring-tables/{table['id']}/versions/import",
        data={"valid_from": "2026-03-01", "norm_reference": REFERENCE},
        headers=headers,
    )

    assert (not_utf8.status_code, not_utf8.json()["detail"][0]["field"]) == (422, "file")
    assert (missing.status_code, missing.json()["detail"][0]["field"]) == (422, "file")
    assert len(official(client)["versions"]) == 1


def test_csv_import_without_norm_reference_is_422_and_unknown_table_404(client, admin):
    _, headers = admin
    table = official(client)

    no_reference = upload(client, headers, table, norm_reference=" ")
    unknown = upload(client, headers, {"id": str(uuid.uuid4())})

    assert (no_reference.status_code, no_reference.json()["detail"][0]["field"]) == (
        422,
        "norm_reference",
    )
    assert unknown.status_code == 404


def test_units_are_replaced_and_audited(client, admin, reference, uow_factory):
    actor, headers = admin
    table = official(client)

    response = client.put(
        f"/api/scoring-tables/{table['id']}/units",
        json={"unit_ids": [str(reference["FASI"].id)]},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["unit_ids"] == [str(reference["FASI"].id)]
    assert set(official(client)["unit_ids"]) == set(response.json()["unit_ids"])
    with uow_factory() as uow:
        [event] = uow.audit.list_for("scoring_table", table["id"])
    assert (event.action, event.user_id) == (AuditAction.UPDATE, actor.id)
    assert set(event.changes["unit_ids"]["before"]) == {
        str(reference["FASI"].id),
        str(reference["IFCH"].id),
    }


def test_units_unknown_unit_is_422_and_unknown_table_404(client, admin):
    _, headers = admin
    table = official(client)

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
    table = official(client)
    assert post_version(client, headers, table).status_code == 201
    assert put_criterion(client, headers, table["versions"][0]["id"]).status_code == 409
    docente_headers = act_as("docente@ufpa.br", Role.DOCENTE)[1]
    assert docente_headers

    response = client.get(f"/api/scoring-tables/{table['id']}/history")

    assert response.status_code == 200
    history = response.json()
    assert [(v["valid_from"], v["valid_to"], v["status"]) for v in history["versions"]] == [
        ("2015-03-24", "2026-02-28", "OFICIAL"),
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
    table = official(client)
    assert post_version(client, headers, table).status_code == 201

    response = put_criterion(client, headers, table["versions"][0]["id"])

    assert response.status_code == 409
    assert "somente leitura" in response.json()["detail"]


# --- GTAB-02, GTAB-04, GTAB-15: mark and clear the version in use of a unit --------------------


def mark(client, headers, unit_id, version_id):
    return client.put(
        f"/api/scoring-units/{unit_id}/default-version",
        json={"version_id": str(version_id)},
        headers=headers,
    )


def stored_mark(uow_factory, unit_id):
    with uow_factory() as uow:
        found = uow.scoring_tables.get_unit_default(unit_id)
    return found.version_id if found else None


def test_put_marks_the_version_and_answers_with_the_unit_and_the_version(
    client, admin, reference, scoring_tables, uow_factory
):
    _, headers = admin
    fasi, version = reference["FASI"], scoring_tables["OFICIAL"]

    response = mark(client, headers, fasi.id, version.id)

    assert response.status_code == 200
    assert response.json() == {"unit_id": str(fasi.id), "version_id": str(version.id)}
    assert stored_mark(uow_factory, fasi.id) == version.id


def test_delete_clears_the_mark_with_204_and_again_with_204(
    client, admin, reference, scoring_tables, uow_factory
):
    _, headers = admin
    fasi = reference["FASI"]
    mark(client, headers, fasi.id, scoring_tables["OFICIAL"].id)

    first = client.delete(f"/api/scoring-units/{fasi.id}/default-version", headers=headers)
    second = client.delete(f"/api/scoring-units/{fasi.id}/default-version", headers=headers)

    assert (first.status_code, second.status_code) == (204, 204)
    assert stored_mark(uow_factory, fasi.id) is None


def test_marking_an_unknown_version_is_404(client, admin, reference):
    _, headers = admin

    response = mark(client, headers, reference["FASI"].id, uuid.uuid4())

    assert response.status_code == 404


def test_marking_for_an_unknown_unit_is_422_on_unit_id(client, admin, scoring_tables):
    _, headers = admin

    response = mark(client, headers, uuid.uuid4(), scoring_tables["OFICIAL"].id)

    assert response.status_code == 422
    assert response.json()["detail"][0]["field"] == "unit_id"


def test_marking_a_table_that_is_not_the_units_is_422_on_unit_id(
    client, admin, reference, scoring_tables, uow_factory
):
    _, headers = admin

    response = mark(client, headers, reference["FASI"].id, scoring_tables["OUTRA"].id)

    assert response.status_code == 422
    assert response.json()["detail"][0]["field"] == "unit_id"
    assert stored_mark(uow_factory, reference["FASI"].id) is None


def test_marking_a_superseded_version_is_409_with_the_code(
    client, admin, reference, legacy_table, scoring_tables
):
    _, headers = admin

    response = mark(client, headers, reference["FASI"].id, scoring_tables["OFICIAL"].id)

    assert response.status_code == 409
    assert response.json()["code"] == "VERSAO_SUBSTITUIDA"


def test_marking_a_version_of_an_archived_table_is_409_with_the_code(
    client, admin, reference, scoring_tables, uow_factory
):
    _, headers = admin
    with uow_factory() as uow:
        uow.scoring_tables.set_table_archived(scoring_tables["OFICIAL"].table_id, True)
        uow.commit()

    response = mark(client, headers, reference["FASI"].id, scoring_tables["OFICIAL"].id)

    assert response.status_code == 409
    assert response.json()["code"] == "TABELA_ARQUIVADA"
    assert stored_mark(uow_factory, reference["FASI"].id) is None


@pytest.mark.parametrize("role", [Role.SECRETARIA, Role.DOCENTE])
def test_marking_and_clearing_are_403_for_non_admin_and_change_nothing(
    client, act_as, reference, scoring_tables, uow_factory, role
):
    _, headers = act_as("outro@ufpa.br", role)
    fasi = reference["FASI"]

    put = mark(client, headers, fasi.id, scoring_tables["OFICIAL"].id)
    delete = client.delete(f"/api/scoring-units/{fasi.id}/default-version", headers=headers)

    assert (put.status_code, delete.status_code) == (403, 403)
    assert stored_mark(uow_factory, fasi.id) is None


# --- GTAB-23, GTAB-26, GTAB-28, GTAB-30, GTAB-31, GTAB-42: archive, preview and delete ---------


def synthetic_table_with_two_versions(client, headers, reference, official_version_id):
    """A synthetic table of FASI with two versions, made through the API."""
    created = client.post(
        "/api/scoring-tables",
        json={
            "name": "Tabela Sintética Z",
            "unit_ids": [str(reference["FASI"].id)],
            "valid_from": "2020-01-01",
            "norm_reference": REFERENCE,
            "base_version_id": str(official_version_id),
        },
        headers=headers,
    ).json()
    second = client.post(
        f"/api/scoring-tables/{created['id']}/versions",
        json={
            "source_version_id": created["versions"][0]["id"],
            "valid_from": "2024-01-01",
            "norm_reference": REFERENCE,
        },
        headers=headers,
    )
    assert second.status_code == 201, second.text
    return created, second.json()


def test_archive_and_unarchive_answer_with_the_table_and_audit_it(
    client, admin, scoring_tables, uow_factory
):
    actor, headers = admin
    table = official(client)

    archived = client.post(f"/api/scoring-tables/{table['id']}/archive", headers=headers)
    unarchived = client.post(f"/api/scoring-tables/{table['id']}/unarchive", headers=headers)

    assert archived.status_code == 200
    assert (archived.json()["id"], archived.json()["archived"]) == (table["id"], True)
    assert unarchived.status_code == 200
    assert unarchived.json()["archived"] is False
    with uow_factory() as uow:
        events = uow.audit.list_for("scoring_table", table["id"])
    assert [(e.action, e.user_id) for e in events] == [
        (AuditAction.ARCHIVE, actor.id),
        (AuditAction.UPDATE, actor.id),
    ]


def test_archiving_a_table_with_a_version_in_use_is_409_with_the_code_and_the_acronyms(
    client, admin, reference, scoring_tables
):
    _, headers = admin
    mark(client, headers, reference["FASI"].id, scoring_tables["OFICIAL"].id)

    response = client.post(f"/api/scoring-tables/{official(client)['id']}/archive", headers=headers)

    assert response.status_code == 409
    assert response.json()["code"] == "TABELA_COM_VERSAO_EM_USO"
    assert "FASI" in response.json()["detail"]
    assert official(client)["archived"] is False


@pytest.mark.parametrize("action", ["archive", "unarchive"])
def test_archiving_an_unknown_table_is_404(client, admin, action):
    _, headers = admin

    response = client.post(f"/api/scoring-tables/{uuid.uuid4()}/{action}", headers=headers)

    assert response.status_code == 404


def test_delete_version_answers_204_and_removes_it(
    client, admin, reference, scoring_tables
):
    _, headers = admin
    _, second = synthetic_table_with_two_versions(
        client, headers, reference, scoring_tables["OFICIAL"].id
    )

    response = client.delete(f"/api/scoring-versions/{second['id']}", headers=headers)

    assert response.status_code == 204
    assert response.content == b""
    assert client.get(f"/api/scoring-versions/{second['id']}").status_code == 404


def test_delete_table_answers_204_and_removes_it_with_its_versions(
    client, admin, reference, scoring_tables
):
    _, headers = admin
    created, second = synthetic_table_with_two_versions(
        client, headers, reference, scoring_tables["OFICIAL"].id
    )

    response = client.delete(f"/api/scoring-tables/{created['id']}", headers=headers)

    assert response.status_code == 204
    assert created["id"] not in [t["id"] for t in client.get("/api/scoring-tables").json()]
    assert client.get(f"/api/scoring-versions/{second['id']}").status_code == 404


def test_deleting_the_official_table_and_one_of_its_versions_is_409_tabela_oficial_protegida(
    client, admin
):
    _, headers = admin
    table = official(client)

    table_response = client.delete(f"/api/scoring-tables/{table['id']}", headers=headers)
    version_response = client.delete(
        f"/api/scoring-versions/{table['versions'][0]['id']}", headers=headers
    )

    for response in (table_response, version_response):
        assert response.status_code == 409
        assert response.json()["code"] == "TABELA_OFICIAL_PROTEGIDA"
        assert "oficial da UFPA" in response.json()["detail"]
    assert len(official(client)["versions"]) == 1


def test_deleting_a_version_used_by_a_process_is_409_with_the_count_in_the_text(
    client, admin, reference, scoring_tables, uow_factory
):
    _, headers = admin
    _, second = synthetic_table_with_two_versions(
        client, headers, reference, scoring_tables["OFICIAL"].id
    )
    professor = add_professor(uow_factory, reference["FASI"])
    process = client.post("/api/processes", json=process_payload(professor), headers=headers).json()
    chosen = client.put(
        f"/api/processes/{process['id']}/scoring/table",
        json={"version_id": second["id"]},
        headers=headers,
    )
    assert chosen.status_code == 200

    response = client.delete(f"/api/scoring-versions/{second['id']}", headers=headers)

    assert response.status_code == 409
    assert response.json()["code"] == "VERSAO_USADA_POR_PROCESSO"
    assert response.json()["detail"] == "A versão é usada por 1 processo e não pode ser excluída"
    assert client.get(f"/api/scoring-versions/{second['id']}").status_code == 200


def test_deleting_a_table_with_a_version_in_use_is_409_with_the_acronyms_in_the_text(
    client, admin, reference, scoring_tables
):
    _, headers = admin
    created, second = synthetic_table_with_two_versions(
        client, headers, reference, scoring_tables["OFICIAL"].id
    )
    assert mark(client, headers, reference["FASI"].id, second["id"]).status_code == 200

    response = client.delete(f"/api/scoring-tables/{created['id']}", headers=headers)

    assert response.status_code == 409
    assert response.json()["code"] == "VERSAO_EM_USO_DE_UNIDADE"
    assert "FASI" in response.json()["detail"]


@pytest.mark.parametrize("kind", ["versions", "tables"])
def test_deleting_an_unknown_version_or_table_is_404(client, admin, kind):
    _, headers = admin
    prefix = "scoring-versions" if kind == "versions" else "scoring-tables"

    assert client.delete(f"/api/{prefix}/{uuid.uuid4()}", headers=headers).status_code == 404
    assert client.get(f"/api/{prefix}/{uuid.uuid4()}/delete-preview").status_code == 404


@pytest.mark.parametrize("role", [Role.ADMIN, Role.SECRETARIA, Role.DOCENTE])
def test_the_previews_are_open_to_every_authenticated_profile(
    client, act_as, reference, scoring_tables, role
):
    _, headers = act_as("quem@ufpa.br", role)
    table = official(client)

    version_id = table["versions"][0]["id"]
    version_preview = client.get(f"/api/scoring-versions/{version_id}/delete-preview")
    table_preview = client.get(f"/api/scoring-tables/{table['id']}/delete-preview")

    assert version_preview.status_code == 200
    assert version_preview.json()["name"] == table["versions"][0]["name"]
    assert version_preview.json()["criteria"] == 100
    assert [b["code"] for b in version_preview.json()["blocked"]][0] == "TABELA_OFICIAL_PROTEGIDA"
    assert table_preview.status_code == 200
    body = table_preview.json()
    assert (body["name"], body["versions"], body["criteria"]) == (OFFICIAL_NAME, 1, 100)
    assert sorted(u["acronym"] for u in body["units"]) == ["FASI", "IFCH"]
    assert body["blocked"][0]["code"] == "TABELA_OFICIAL_PROTEGIDA"
    assert set(body["blocked"][0]) == {"code", "message", "count", "acronyms"}


def test_the_preview_of_a_free_table_has_no_blocker_and_the_blockers_carry_count_and_acronyms(
    client, admin, reference, scoring_tables
):
    _, headers = admin
    created, second = synthetic_table_with_two_versions(
        client, headers, reference, scoring_tables["OFICIAL"].id
    )
    free = client.get(f"/api/scoring-tables/{created['id']}/delete-preview").json()
    assert free["blocked"] == []
    assert (free["versions"], free["criteria"]) == (2, 200)
    mark(client, headers, reference["FASI"].id, second["id"])

    marked = client.get(f"/api/scoring-versions/{second['id']}/delete-preview").json()

    assert marked["blocked"] == [
        {
            "code": "VERSAO_EM_USO_DE_UNIDADE",
            "message": (
                "A versão está em uso das unidades FASI; marque outra versão ou desmarque-a "
                "antes de excluir"
            ),
            "count": None,
            "acronyms": ["FASI"],
        }
    ]


# --- F12: the answer of a write is the table as the list shows it, with the block reasons ---------


def listed(client, table_id):
    return next(t for t in client.get("/api/scoring-tables").json() if t["id"] == table_id)


def test_the_answers_of_the_table_writes_carry_the_same_block_reasons_as_the_list(
    client, admin, reference
):
    _, headers = admin
    table = official(client)
    new_body = {
        "name": "Tabela Sintética Resposta",
        "unit_ids": [],
        "valid_from": "2026-01-01",
        "norm_reference": REFERENCE,
    }

    writes = {
        "units": lambda: client.put(
            f"/api/scoring-tables/{table['id']}/units",
            json={"unit_ids": [str(reference["FASI"].id)]},
            headers=headers,
        ),
        "archive": lambda: client.post(
            f"/api/scoring-tables/{table['id']}/archive", headers=headers
        ),
        "unarchive": lambda: client.post(
            f"/api/scoring-tables/{table['id']}/unarchive", headers=headers
        ),
        "create": lambda: client.post("/api/scoring-tables", json=new_body, headers=headers),
        "duplicate": lambda: client.post(
            f"/api/scoring-tables/{table['id']}/duplicate",
            json={"new_name": "Cópia Sintética Resposta"},
            headers=headers,
        ),
    }

    answers = {}
    for name, write in writes.items():
        response = write()
        assert response.status_code in (200, 201), name
        assert response.json() == listed(client, response.json()["id"]), name
        answers[name] = response
    # the official table is protected from deletion, and the answers say so (not a null)
    assert answers["units"].json()["delete_blocked_reason"] == "TABELA_OFICIAL_PROTEGIDA"
    # the only version of a new table cannot be deleted: its own reason is in the answer
    [only] = answers["create"].json()["versions"]
    assert only["delete_blocked_reason"] == "ULTIMA_VERSAO_DA_TABELA"
