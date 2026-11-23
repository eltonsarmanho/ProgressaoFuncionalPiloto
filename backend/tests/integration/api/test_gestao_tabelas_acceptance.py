"""GTAB acceptance: the independent tests of the spec, end to end through the API.

Synthetic data only. One scenario walks the whole life of the tables of a unit (mark, switch,
archive, delete, restart of the seed) and checks that a process that already chose its table and
the documents generated for it never change; a second one checks the roles.
"""

import pytest

from app.domain.entities.audit import AuditAction
from app.domain.entities.user import Role
from app.infrastructure.database.seed import seed_scoring_tables, seed_unit_defaults
from tests.integration.api.conftest import login
from tests.integration.api.factories import add_professor, process_payload
from tests.integration.api.generated_support import (
    add_activity,
    choose_table,
    file_url,
    generate,
    generations_url,
    sha256,
)
from tests.integration.api.test_scoring_admin_api import REFERENCE, official, write_requests
from tests.integration.test_seed_scoring import LEGACY, _add_legacy_table

DEFAULT = "unit_scoring_default"
COPY_NAME = "Tabela Sintética FASI Cópia"


def table_url(process) -> str:
    return f"/api/processes/{process['id']}/scoring/table"


def new_process(client, headers, uow_factory, unit, siape) -> dict:
    professor = add_professor(uow_factory, unit, siape=siape, name=f"Docente {siape}")
    response = client.post("/api/processes", json=process_payload(professor), headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def state(client, process) -> dict:
    response = client.get(table_url(process))
    assert response.status_code == 200, response.text
    return response.json()


def suggested_id(client, process) -> str:
    return state(client, process)["suggested"]["version"]["id"]


def put_default(client, headers, unit, version_id):
    return client.put(
        f"/api/scoring-units/{unit.id}/default-version",
        json={"version_id": str(version_id)},
        headers=headers,
    )


def clear_default(client, headers, unit):
    return client.delete(f"/api/scoring-units/{unit.id}/default-version", headers=headers)


def events(uow_factory, entity, entity_id):
    # In the order they were written: the API runs on the fake clock and the seed on the real one.
    with uow_factory() as uow:
        return sorted(uow.audit.list_for(entity, str(entity_id)), key=lambda e: e.id)


def tables(client) -> dict:
    return {t["name"]: t for t in client.get("/api/scoring-tables").json()}


def by_id(client, table_name) -> dict:
    return {v["id"]: v for v in tables(client)[table_name]["versions"]}


def test_the_table_management_flow_end_to_end(
    client, admin, reference, scoring_tables, uow_factory
):
    actor, headers = admin
    fasi, ifch = reference["FASI"], reference["IFCH"]
    official_version = scoring_tables["OFICIAL"]
    official_id = str(official_version.id)

    # An existing process that already chose the official table, with a validated activity and a
    # generated Tabela de Pontuação: what no step below may change (GTAB-08, AD-012).
    existing = new_process(client, headers, uow_factory, fasi, "3000001")
    choose_table(client, headers, existing, official_version)
    add_activity(client, headers, existing)
    generated = generate(client, headers, existing, "TABELA")
    pdf_before = sha256(client.get(file_url(generated, "pdf")).content)
    score_before = client.get(f"/api/processes/{existing['id']}/scoring").json()
    list_before = client.get(generations_url(existing)).json()

    # Two versions of a table of FASI (the copy of the official one, then a new version).
    copy = client.post(
        f"/api/scoring-tables/{official(client)['id']}/duplicate",
        json={"new_name": COPY_NAME, "unit_ids": [str(fasi.id)]},
        headers=headers,
    )
    assert copy.status_code == 201, copy.text
    copy_table = copy.json()
    [v1] = copy_table["versions"]
    created = client.post(
        f"/api/scoring-tables/{copy_table['id']}/versions",
        json={
            "source_version_id": v1["id"],
            "valid_from": "2026-03-01",
            "norm_reference": REFERENCE,
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    v2 = created.json()
    assert by_id(client, COPY_NAME)[v1["id"]]["valid_to"] == "2026-02-28"  # ADM-05 closed it

    # GTAB-01, GTAB-02, GTAB-05: mark the second version; a new process is suggested it, and
    # does not receive it.
    novo = new_process(client, headers, uow_factory, fasi, "3000002")
    marked = put_default(client, headers, fasi, v2["id"])
    assert marked.status_code == 200, marked.text
    assert marked.json() == {"unit_id": str(fasi.id), "version_id": v2["id"]}
    assert suggested_id(client, novo) == v2["id"]
    assert state(client, novo)["chosen"] is None
    history = client.get(f"/api/processes/{novo['id']}/history").json()
    assert not any("scoring_table_version_id" in e["changes"] for e in history)
    [created_mark] = events(uow_factory, DEFAULT, fasi.id)
    assert (created_mark.action, created_mark.user_id) == (AuditAction.CREATE, actor.id)
    assert created_mark.changes == {"version_id": {"before": None, "after": v2["id"]}}
    assert by_id(client, COPY_NAME)[v2["id"]]["default_for_unit_ids"] == [str(fasi.id)]

    # Switching the mark changes the suggestion; the process that had chosen keeps its table.
    assert put_default(client, headers, fasi, official_id).status_code == 200
    assert suggested_id(client, novo) == official_id
    assert put_default(client, headers, fasi, v2["id"]).status_code == 200
    assert suggested_id(client, novo) == v2["id"]
    assert state(client, existing)["chosen"]["version"]["id"] == official_id  # GTAB-08
    assert [e.action for e in events(uow_factory, DEFAULT, fasi.id)] == [
        AuditAction.CREATE,
        AuditAction.UPDATE,
        AuditAction.UPDATE,
    ]

    # GTAB-25: a table with a version in use is not archived; clearing the mark allows it.
    refused = client.post(f"/api/scoring-tables/{copy_table['id']}/archive", headers=headers)
    assert (refused.status_code, refused.json()["code"]) == (409, "TABELA_COM_VERSAO_EM_USO")
    assert tables(client)[COPY_NAME]["archive_blocked_reason"] == "TABELA_COM_VERSAO_EM_USO"
    assert clear_default(client, headers, fasi).status_code == 204
    assert events(uow_factory, DEFAULT, fasi.id)[-1].action is AuditAction.DELETE
    archived = client.post(f"/api/scoring-tables/{copy_table['id']}/archive", headers=headers)
    assert archived.status_code == 200, archived.text
    assert archived.json()["archived"] is True
    [archive_event] = [
        e
        for e in events(uow_factory, "scoring_table", copy_table["id"])
        if e.action is AuditAction.ARCHIVE
    ]
    assert (archive_event.user_id, archive_event.changes) == (
        actor.id,
        {"archived": {"before": False, "after": True}},
    )

    # GTAB-24: archived, it is out of the suggestion, of the choice and of the marking.
    assert suggested_id(client, novo) == official_id
    choice = client.put(table_url(novo), json={"version_id": v1["id"]}, headers=headers)
    assert (choice.status_code, choice.json()["code"]) == (409, "TABELA_ARQUIVADA")
    again = put_default(client, headers, fasi, v2["id"])
    assert (again.status_code, again.json()["code"]) == (409, "TABELA_ARQUIVADA")
    assert state(client, novo)["chosen"] is None

    # Unarchiving brings it back and marks no version again (edge case).
    unarchived = client.post(f"/api/scoring-tables/{copy_table['id']}/unarchive", headers=headers)
    assert unarchived.status_code == 200 and unarchived.json()["archived"] is False
    assert all(
        v["default_for_unit_ids"] == [] for t in tables(client).values() for v in t["versions"]
    )

    # GTAB-26: delete the newest version, which nothing uses; the previous one is reopened.
    preview = client.get(f"/api/scoring-versions/{v2['id']}/delete-preview")
    assert preview.status_code == 200
    assert preview.json()["blocked"] == [] and preview.json()["criteria"] > 0
    deleted = client.delete(f"/api/scoring-versions/{v2['id']}", headers=headers)
    assert deleted.status_code == 204
    assert list(by_id(client, COPY_NAME)) == [v1["id"]]
    assert by_id(client, COPY_NAME)[v1["id"]]["valid_to"] is None
    [delete_event] = events(uow_factory, "scoring_version", v2["id"])[-1:]
    assert (delete_event.action, delete_event.user_id) == (AuditAction.DELETE, actor.id)
    assert delete_event.changes["name"]["before"] == v2["name"]
    assert client.get(f"/api/scoring-versions/{v2['id']}").status_code == 404

    # GTAB-27, GTAB-42: the version a process uses and the official one are refused with the code.
    assert (
        client.put(table_url(novo), json={"version_id": v1["id"]}, headers=headers).status_code
        == 200
    )
    used = client.delete(f"/api/scoring-versions/{v1['id']}", headers=headers)
    assert (used.status_code, used.json()["code"]) == (409, "VERSAO_USADA_POR_PROCESSO")
    assert "1 processo" in used.json()["detail"]
    protected = client.delete(f"/api/scoring-versions/{official_id}", headers=headers)
    assert (protected.status_code, protected.json()["code"]) == (409, "TABELA_OFICIAL_PROTEGIDA")
    protected_table = client.delete(
        f"/api/scoring-tables/{official(client)['id']}", headers=headers
    )
    assert protected_table.status_code == 409
    assert protected_table.json()["code"] == "TABELA_OFICIAL_PROTEGIDA"
    assert v1["id"] in by_id(client, COPY_NAME) and official_id in by_id(client, OFFICIAL)

    # GTAB-28, GTAB-32: delete the table with its preview once no process uses it.
    blocked = client.get(f"/api/scoring-tables/{copy_table['id']}/delete-preview").json()
    assert [b["code"] for b in blocked["blocked"]] == ["VERSAO_USADA_POR_PROCESSO"]
    assert (
        client.put(table_url(novo), json={"version_id": official_id}, headers=headers).status_code
        == 200
    )
    preview = client.get(f"/api/scoring-tables/{copy_table['id']}/delete-preview").json()
    assert (preview["name"], preview["versions"], preview["blocked"]) == (COPY_NAME, 1, [])
    assert preview["criteria"] > 0
    assert [u["acronym"] for u in preview["units"]] == ["FASI"]
    assert (
        client.delete(f"/api/scoring-tables/{copy_table['id']}", headers=headers).status_code == 204
    )
    assert COPY_NAME not in tables(client)
    [table_deleted] = [
        e
        for e in events(uow_factory, "scoring_table", copy_table["id"])
        if e.action is AuditAction.DELETE
    ]
    assert table_deleted.user_id == actor.id
    assert table_deleted.changes["name"]["before"] == COPY_NAME
    assert table_deleted.changes["criteria"]["before"] == preview["criteria"]

    # GTAB-09: a restart marks the unit nobody ever marked and leaves the one that was cleared.
    units = {u.acronym: u.id for u in reference.values()}
    seed_unit_defaults(uow_factory())
    assert by_id(client, OFFICIAL)[official_id]["default_for_unit_ids"] == [str(ifch.id)]
    [system_mark] = events(uow_factory, DEFAULT, ifch.id)
    assert (system_mark.user_id, system_mark.action) == (None, AuditAction.CREATE)
    assert clear_default(client, headers, ifch).status_code == 204
    seed_unit_defaults(uow_factory())  # the cleared unit stays cleared
    seed_unit_defaults(uow_factory())
    assert by_id(client, OFFICIAL)[official_id]["default_for_unit_ids"] == []
    assert [e.action for e in events(uow_factory, DEFAULT, ifch.id)] == [
        AuditAction.CREATE,
        AuditAction.DELETE,
    ]
    assert [e.action for e in events(uow_factory, DEFAULT, fasi.id)][-1] is AuditAction.DELETE

    # GTAB-41: a legacy table the ADMIN unarchived stays unarchived after the seed runs again.
    legacy_id = _add_legacy_table(uow_factory, units, LEGACY[0], "IFCH")
    seed_scoring_tables(uow_factory())  # OFI-09: nobody touched it, so it is archived
    assert tables(client)[LEGACY[0]]["archived"] is True
    back = client.post(f"/api/scoring-tables/{legacy_id}/unarchive", headers=headers)
    assert back.status_code == 200 and back.json()["archived"] is False
    reassociated = client.put(
        f"/api/scoring-tables/{legacy_id}/units",
        json={"unit_ids": [str(ifch.id)]},
        headers=headers,
    )
    assert reassociated.status_code == 200
    seed_scoring_tables(uow_factory())
    assert tables(client)[LEGACY[0]]["archived"] is False
    assert tables(client)[LEGACY[0]]["unit_ids"] == [str(ifch.id)]

    # GTAB-08, AD-012: the existing process and its generated documents did not change.
    assert state(client, existing)["chosen"]["version"]["id"] == official_id
    assert client.get(f"/api/processes/{existing['id']}/scoring").json() == score_before
    assert client.get(generations_url(existing)).json() == list_before
    assert sha256(client.get(file_url(generated, "pdf")).content) == pdf_before


OFFICIAL = "Tabela de Pontuação da UFPA"


@pytest.mark.parametrize("role", [Role.SECRETARIA, Role.DOCENTE])
def test_a_user_who_is_not_admin_reads_the_tables_and_is_refused_every_write(
    client, make_user, admin, reference, scoring_tables, role
):
    table = official(client)  # the admin session reads the list; the actor changes below
    other = make_user(f"{role.lower()}-leitor@ufpa.br", role)
    client.post("/api/auth/logout", headers=admin[1])
    headers = {"X-CSRF-Token": login(client, other.email)}

    listing = client.get("/api/scoring-tables")
    assert listing.status_code == 200
    assert {t["name"] for t in listing.json()} >= {OFFICIAL}
    version_id = table["versions"][0]["id"]
    assert client.get(f"/api/scoring-versions/{version_id}").status_code == 200
    assert client.get(f"/api/scoring-versions/{version_id}/delete-preview").status_code == 200
    assert client.get(f"/api/scoring-tables/{table['id']}/delete-preview").status_code == 200

    writes = write_requests(client, headers, table, reference)

    assert {name: r.status_code for name, r in writes.items()} == {name: 403 for name in writes}
    after = {t["name"]: t for t in client.get("/api/scoring-tables").json()}
    assert set(after) == {t["name"] for t in listing.json()}
    assert not after[OFFICIAL]["archived"]
    assert all(v["default_for_unit_ids"] == [] for v in after[OFFICIAL]["versions"])
