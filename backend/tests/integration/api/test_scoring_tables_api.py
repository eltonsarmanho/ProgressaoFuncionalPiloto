"""TAB-08: read routes for scoring tables, versions and criteria."""

import uuid

import pytest

from app.domain.entities.user import Role
from tests.integration.api.factories import add_professor, process_payload

GROUP_COUNTS = [2, 16, 9, 6, 5, 14, 11, 37]
OFFICIAL_NAME = "Tabela de Pontuação da UFPA"
OTHER_NAME = "Tabela Sintética Alternativa de Teste"


@pytest.fixture
def docente(act_as, scoring_tables):
    return act_as("docente@ufpa.br", Role.DOCENTE)


def tables_by_name(client):
    response = client.get("/api/scoring-tables")
    assert response.status_code == 200
    return {t["name"]: t for t in response.json()}


def version_detail(client, scoring_tables, key):
    response = client.get(f"/api/scoring-versions/{scoring_tables[key].id}")
    assert response.status_code == 200
    return response.json()


def test_lists_the_seeded_tables_with_versions_validity_status_and_reference(
    client, docente, scoring_tables, reference
):
    tables = tables_by_name(client)

    assert set(tables) == {OFFICIAL_NAME, OTHER_NAME}
    official, other = tables[OFFICIAL_NAME], tables[OTHER_NAME]
    assert set(official["unit_ids"]) == {str(reference["FASI"].id), str(reference["IFCH"].id)}
    assert other["unit_ids"] == []
    [version] = official["versions"]
    assert version["id"] == str(scoring_tables["OFICIAL"].id)
    assert version["status"] == "OFICIAL"
    assert version["valid_from"] == "2015-03-24"
    assert version["valid_to"] is None
    assert version["norm_reference"] == (
        "Tabela oficial de pontuação para progressão docente da UFPA "
        "(planilha fornecida pelo usuário em 2026-11-17)"
    )
    assert version["in_use"] is False


def test_versions_of_a_table(client, docente, scoring_tables):
    table = tables_by_name(client)[OFFICIAL_NAME]

    response = client.get(f"/api/scoring-tables/{table['id']}/versions")

    assert response.status_code == 200
    assert response.json() == table["versions"]


def test_unknown_table_has_no_versions(client, docente):
    assert client.get(f"/api/scoring-tables/{uuid.uuid4()}/versions").status_code == 404


def test_version_has_eight_groups_and_criteria_in_group_and_item_order(
    client, docente, scoring_tables
):
    detail = version_detail(client, scoring_tables, "OFICIAL")

    assert [g["number"] for g in detail["groups"]] == list(range(1, 9))
    assert [len(g["criteria"]) for g in detail["groups"]] == GROUP_COUNTS
    for group in detail["groups"]:
        assert [c["item_number"] for c in group["criteria"]] == list(
            range(1, len(group["criteria"]) + 1)
        )
        assert {c["group_number"] for c in group["criteria"]} == {group["number"]}


def test_decimals_are_text_with_two_places_and_never_numbers(client, docente, scoring_tables):
    detail = version_detail(client, scoring_tables, "OFICIAL")
    groups = {g["number"]: {c["item_number"]: c for c in g["criteria"]} for g in detail["groups"]}

    assert groups[2][7]["unit_points"] == "5.00"
    assert groups[2][7]["max_points"] is None
    assert groups[1][1]["unit_points"] is None
    assert groups[7][11]["hours_per_block"] == "30.00"
    assert groups[7][11]["unit_points"] == "1.00"
    assert groups[1][1]["mode"] == "CARGA_SEMANAL"
    assert (groups[1][1]["weeks_per_semester"], groups[1][1]["prep_ratio"]) == (17, "1.00")
    assert (groups[1][2]["weeks_per_semester"], groups[1][2]["prep_ratio"]) == (17, "2.00")


def test_group_one_is_outside_the_total_and_the_minimums_are_exposed(
    client, docente, scoring_tables
):
    official = version_detail(client, scoring_tables, "OFICIAL")

    assert official["groups"][0]["counts_in_total"] is False
    assert all(g["counts_in_total"] for g in official["groups"][1:])
    assert official["status"] == "OFICIAL"
    assert official["minimums"]["by_current_class"] == {"A": 60, "B": 80, "C": 100, "D": 120}


def test_review_notes_are_exposed(client, docente, scoring_tables):
    detail = version_detail(client, scoring_tables, "OFICIAL")
    group2 = {c["item_number"]: c for c in detail["groups"][1]["criteria"]}

    assert group2[10]["review_note"]
    assert group2[7]["review_note"] is None


def test_version_in_use_is_flagged_after_a_process_chooses_it(
    client, act_as, scoring_tables, reference, uow_factory
):
    actor, headers = act_as("admin@ufpa.br", Role.ADMIN)
    professor = add_professor(uow_factory, reference["FASI"])
    process = client.post("/api/processes", json=process_payload(professor), headers=headers)
    with uow_factory() as uow:
        process_id = uuid.UUID(process.json()["id"])
        uow.processes.set_scoring_table_version(process_id, scoring_tables["OFICIAL"].id)
        uow.commit()

    assert version_detail(client, scoring_tables, "OFICIAL")["in_use"] is True
    assert version_detail(client, scoring_tables, "OUTRA")["in_use"] is False


def test_unknown_version_is_404_and_malformed_id_is_422(client, docente):
    assert client.get(f"/api/scoring-versions/{uuid.uuid4()}").status_code == 404
    response = client.get("/api/scoring-versions/not-a-uuid")
    assert response.status_code == 422
    assert response.json()["detail"][0]["field"] == "version_id"


@pytest.mark.parametrize("role", [Role.ADMIN, Role.SECRETARIA, Role.DOCENTE])
def test_every_role_may_read(client, act_as, scoring_tables, role):
    act_as(f"{role.lower()}@ufpa.br", role)

    assert client.get("/api/scoring-tables").status_code == 200
    assert client.get(f"/api/scoring-versions/{scoring_tables["OFICIAL"].id}").status_code == 200


def test_routes_require_a_session(client, scoring_tables):
    table_id = uuid.uuid4()
    for url in (
        "/api/scoring-tables",
        f"/api/scoring-tables/{table_id}/versions",
        f"/api/scoring-versions/{scoring_tables["OFICIAL"].id}",
    ):
        assert client.get(url).status_code == 401
