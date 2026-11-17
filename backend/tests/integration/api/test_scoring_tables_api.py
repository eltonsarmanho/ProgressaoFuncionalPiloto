"""TAB-08: read routes for scoring tables, versions and criteria."""

import uuid

import pytest

from app.domain.entities.user import Role
from tests.integration.api.factories import add_professor, process_payload

GROUP_COUNTS = [3, 16, 12, 7, 6, 14, 11, 66]
FASI_NAME = "Tabela de Pontuação da FASI"
IFCH_NAME = "Tabela de Pontuação do IFCH"


@pytest.fixture
def docente(act_as, scoring_tables):
    return act_as("docente@ufpa.br", Role.DOCENTE)


def tables_by_name(client):
    response = client.get("/api/scoring-tables")
    assert response.status_code == 200
    return {t["name"]: t for t in response.json()}


def version_detail(client, scoring_tables, unit):
    response = client.get(f"/api/scoring-versions/{scoring_tables[unit].id}")
    assert response.status_code == 200
    return response.json()


def test_lists_both_seeded_tables_with_versions_validity_status_and_reference(
    client, docente, scoring_tables, reference
):
    tables = tables_by_name(client)

    assert set(tables) == {FASI_NAME, IFCH_NAME}
    fasi, ifch = tables[FASI_NAME], tables[IFCH_NAME]
    assert fasi["unit_ids"] == [str(reference["FASI"].id)]
    assert ifch["unit_ids"] == [str(reference["IFCH"].id)]
    [fasi_version] = fasi["versions"]
    assert fasi_version["id"] == str(scoring_tables["FASI"].id)
    assert fasi_version["status"] == "PENDENTE_VALIDACAO"
    assert fasi_version["valid_from"] == "2022-11-23"
    assert fasi_version["valid_to"] is None
    assert fasi_version["norm_reference"].startswith("Tabela preenchida FASI/Campus Cametá")
    assert fasi_version["in_use"] is False
    [ifch_version] = ifch["versions"]
    assert ifch_version["status"] == "OFICIAL"
    assert ifch_version["norm_reference"] == (
        "Tabela de Pontuação do IFCH em complementação ao Anexo I da Res. 4.644/2015-CONSEPE"
    )


def test_versions_of_a_table(client, docente, scoring_tables):
    table = tables_by_name(client)[FASI_NAME]

    response = client.get(f"/api/scoring-tables/{table['id']}/versions")

    assert response.status_code == 200
    assert response.json() == table["versions"]


def test_unknown_table_has_no_versions(client, docente):
    assert client.get(f"/api/scoring-tables/{uuid.uuid4()}/versions").status_code == 404


def test_version_has_eight_groups_and_criteria_in_group_and_item_order(
    client, docente, scoring_tables
):
    detail = version_detail(client, scoring_tables, "FASI")

    assert [g["number"] for g in detail["groups"]] == list(range(1, 9))
    assert [len(g["criteria"]) for g in detail["groups"]] == GROUP_COUNTS
    for group in detail["groups"]:
        assert [c["item_number"] for c in group["criteria"]] == list(
            range(1, len(group["criteria"]) + 1)
        )
        assert {c["group_number"] for c in group["criteria"]} == {group["number"]}


def test_decimals_are_text_with_two_places_and_never_numbers(client, docente, scoring_tables):
    detail = version_detail(client, scoring_tables, "FASI")
    groups = {g["number"]: {c["item_number"]: c for c in g["criteria"]} for g in detail["groups"]}

    assert groups[2][7]["unit_points"] == "10.00"
    assert groups[1][3]["max_points"] == "10.00"
    assert groups[1][3]["unit_points"] is None
    assert groups[4][4]["hours_per_block"] == "3.00"
    assert groups[1][1]["mode"] == "CARGA_SEMANAL"
    assert (groups[1][1]["weeks_per_semester"], groups[1][1]["prep_ratio"]) == (17, "1.00")
    assert (groups[1][2]["weeks_per_semester"], groups[1][2]["prep_ratio"]) == (17, "2.00")


def test_group_one_counts_in_total_only_for_fasi(client, docente, scoring_tables):
    fasi = version_detail(client, scoring_tables, "FASI")
    ifch = version_detail(client, scoring_tables, "IFCH")

    assert fasi["groups"][0]["counts_in_total"] is True
    assert ifch["groups"][0]["counts_in_total"] is False
    assert ifch["status"] == "OFICIAL"
    assert ifch["minimums"]["by_current_class"] == {"A": 60, "B": 80, "C": 100, "D": 120}


def test_fasi_review_notes_are_exposed(client, docente, scoring_tables):
    detail = version_detail(client, scoring_tables, "FASI")
    group2 = {c["item_number"]: c for c in detail["groups"][1]["criteria"]}

    assert group2[9]["review_note"]
    assert group2[7]["review_note"] is None


def test_version_in_use_is_flagged_after_a_process_chooses_it(
    client, act_as, scoring_tables, reference, uow_factory
):
    actor, headers = act_as("admin@ufpa.br", Role.ADMIN)
    professor = add_professor(uow_factory, reference["FASI"])
    process = client.post("/api/processes", json=process_payload(professor), headers=headers)
    with uow_factory() as uow:
        process_id = uuid.UUID(process.json()["id"])
        uow.processes.set_scoring_table_version(process_id, scoring_tables["FASI"].id)
        uow.commit()

    assert version_detail(client, scoring_tables, "FASI")["in_use"] is True
    assert version_detail(client, scoring_tables, "IFCH")["in_use"] is False


def test_unknown_version_is_404_and_malformed_id_is_422(client, docente):
    assert client.get(f"/api/scoring-versions/{uuid.uuid4()}").status_code == 404
    response = client.get("/api/scoring-versions/not-a-uuid")
    assert response.status_code == 422
    assert response.json()["detail"][0]["field"] == "version_id"


@pytest.mark.parametrize("role", [Role.ADMIN, Role.SECRETARIA, Role.DOCENTE])
def test_every_role_may_read(client, act_as, scoring_tables, role):
    act_as(f"{role.lower()}@ufpa.br", role)

    assert client.get("/api/scoring-tables").status_code == 200
    assert client.get(f"/api/scoring-versions/{scoring_tables['FASI'].id}").status_code == 200


def test_routes_require_a_session(client, scoring_tables):
    table_id = uuid.uuid4()
    for url in (
        "/api/scoring-tables",
        f"/api/scoring-tables/{table_id}/versions",
        f"/api/scoring-versions/{scoring_tables['FASI'].id}",
    ):
        assert client.get(url).status_code == 401
