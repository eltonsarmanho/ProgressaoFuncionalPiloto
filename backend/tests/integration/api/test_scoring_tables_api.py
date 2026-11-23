"""TAB-08: read routes for scoring tables, versions and criteria."""

import uuid
from datetime import date

import pytest
from sqlalchemy import event

from app.application.use_cases.scoring_admin import ListScoringTables, ProtectedCatalog
from app.domain.entities.user import Role
from app.domain.repositories.ports import ScoringTableRecord
from tests.integration.api.factories import add_professor, process_payload
from tests.integration.test_scoring_repositories import make_version

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
        "(planilha fornecida em 2026-11-17), com o Grupo I somado ao total a 1 ponto por hora "
        "de PIT por decisão do usuário em 2026-11-19"
    )  # GI-07: the seeded version is the one with group I in the total
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


def test_every_group_counts_in_the_total_and_the_minimums_are_exposed(
    client, docente, scoring_tables
):
    official = version_detail(client, scoring_tables, "OFICIAL")

    # GI-07: was "group I is outside the total" (PIT-01); the seeded version counts it.
    assert all(g["counts_in_total"] for g in official["groups"])
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


def test_a_superseded_version_lists_the_version_that_replaced_it(
    client, docente, scoring_tables, uow_factory
):
    # GI-07: superseded_by_id is filled on the old version and null on the new one
    from tests.support.scoring_variants import add_legacy_ufpa_version

    new = scoring_tables["OFICIAL"]
    with uow_factory() as uow:
        old = add_legacy_ufpa_version(uow, new)
        uow.scoring_tables.set_superseded(old.id, new.id)
        uow.commit()

    official = tables_by_name(client)[OFFICIAL_NAME]

    by_id = {v["id"]: v["superseded_by_id"] for v in official["versions"]}
    assert by_id == {str(old.id): str(new.id), str(new.id): None}
    one = client.get(f"/api/scoring-versions/{old.id}").json()
    assert one["superseded_by_id"] == str(new.id)


# --- GTAB-10: process count and the units that have the version in use -------------------------


def versions_by_id(client):
    return {
        v["id"]: v for table in client.get("/api/scoring-tables").json() for v in table["versions"]
    }


def add_processes_on(client, headers, uow_factory, unit, version_id, count, first_siape):
    """`count` processes of `count` professors of the unit, each with the version chosen."""
    for n in range(count):
        professor = add_professor(uow_factory, unit, siape=str(first_siape + n))
        created = client.post("/api/processes", json=process_payload(professor), headers=headers)
        assert created.status_code == 201, created.text
        with uow_factory() as uow:
            uow.processes.set_scoring_table_version(uuid.UUID(created.json()["id"]), version_id)
            uow.commit()


def test_process_count_is_0_1_and_2_and_in_use_means_some_process_uses_it(
    client, act_as, scoring_tables, reference, uow_factory
):
    _, headers = act_as("admin@ufpa.br", Role.ADMIN)
    official, other = scoring_tables["OFICIAL"], scoring_tables["OUTRA"]
    before = versions_by_id(client)
    assert (before[str(official.id)]["process_count"], before[str(other.id)]["process_count"]) == (
        0,
        0,
    )

    add_processes_on(client, headers, uow_factory, reference["FASI"], other.id, 1, 2000001)
    add_processes_on(client, headers, uow_factory, reference["FASI"], official.id, 2, 2000011)

    after = versions_by_id(client)
    assert after[str(other.id)]["process_count"] == 1
    assert after[str(official.id)]["process_count"] == 2
    assert after[str(other.id)]["in_use"] is True
    assert after[str(official.id)]["in_use"] is True
    assert version_detail(client, scoring_tables, "OFICIAL")["process_count"] == 2


def test_default_for_unit_ids_follows_the_marks_and_does_not_make_the_version_in_use(
    client, docente, scoring_tables, reference, uow_factory
):
    official, other = scoring_tables["OFICIAL"], scoring_tables["OUTRA"]
    fasi, ifch = reference["FASI"], reference["IFCH"]
    with uow_factory() as uow:
        uow.scoring_tables.set_unit_default(fasi.id, official.id)
        uow.scoring_tables.set_unit_default(ifch.id, official.id)
        uow.commit()

    marked = versions_by_id(client)
    assert sorted(marked[str(official.id)]["default_for_unit_ids"]) == sorted(
        [str(fasi.id), str(ifch.id)]
    )
    assert marked[str(other.id)]["default_for_unit_ids"] == []
    assert marked[str(official.id)]["in_use"] is False  # in use means "a process uses it"
    assert marked[str(official.id)]["process_count"] == 0
    assert version_detail(client, scoring_tables, "OFICIAL")["default_for_unit_ids"] == (
        marked[str(official.id)]["default_for_unit_ids"]
    )

    with uow_factory() as uow:
        uow.scoring_tables.clear_unit_default(fasi.id)
        uow.commit()

    assert versions_by_id(client)[str(official.id)]["default_for_unit_ids"] == [str(ifch.id)]


def _count_statements(engine, call) -> int:
    seen: list[str] = []

    def record(conn, cursor, statement, *args):
        seen.append(statement)

    event.listen(engine, "before_cursor_execute", record)
    try:
        call()
    finally:
        event.remove(engine, "before_cursor_execute", record)
    return len(seen)


def test_the_number_of_queries_of_the_list_does_not_grow_with_the_versions(engine, uow_factory):
    tables = [ScoringTableRecord(uuid.uuid4(), f"Tabela Sintética {n}") for n in range(3)]
    with uow_factory() as uow:
        for table in tables:
            uow.scoring_tables.add_table(table)
            uow.scoring_tables.add_version(make_version(table.id, name="v1"))
        uow.commit()
    use_case = ListScoringTables(uow_factory, ProtectedCatalog(OFFICIAL_NAME))

    with_one_version = _count_statements(engine, use_case.execute)
    with uow_factory() as uow:
        for table in tables:
            for n in range(2, 6):
                uow.scoring_tables.add_version(make_version(table.id, name=f"v{n}"))
        uow.commit()
    with_five_versions = _count_statements(engine, use_case.execute)

    assert [len(v.versions) for v in use_case.execute()] == [5, 5, 5]
    assert with_five_versions == with_one_version


# --- GTAB-36: why a version or a table cannot be edited, archived or deleted -----------------


def synthetic_table(uow_factory, name, starts, unit_ids=()):
    """A synthetic table with one version per start date; returns the table and its versions."""
    table = ScoringTableRecord(uuid.uuid4(), name, unit_ids=tuple(unit_ids))
    versions = [make_version(table.id, name=f"v{n}", valid_from=d) for n, d in enumerate(starts)]
    with uow_factory() as uow:
        uow.scoring_tables.add_table(table)
        for version in versions:
            uow.scoring_tables.add_version(version)
        uow.commit()
    return table, versions


def table_json(client, table):
    return next(t for t in client.get("/api/scoring-tables").json() if t["id"] == str(table.id))


def reasons(version_json):
    return version_json["read_only_reason"], version_json["delete_blocked_reason"]


def choose_in_a_process(client, headers, uow_factory, unit, version, siape):
    add_processes_on(client, headers, uow_factory, unit, version.id, 1, siape)


def test_a_version_used_by_a_process_is_read_only_and_not_deletable_for_that_reason(
    client, act_as, scoring_tables, reference, uow_factory
):
    _, headers = act_as("admin@ufpa.br", Role.ADMIN)
    table, [first, second] = synthetic_table(
        uow_factory, "Tabela Sintética Usada", [date(2020, 1, 1), date(2021, 1, 1)]
    )
    choose_in_a_process(client, headers, uow_factory, reference["FASI"], second, 2100001)

    listed = table_json(client, table)
    by_id = {v["id"]: v for v in listed["versions"]}

    used = "VERSAO_USADA_POR_PROCESSO"
    assert reasons(by_id[str(second.id)]) == (used, used)
    assert listed["delete_blocked_reason"] == "VERSAO_USADA_POR_PROCESSO"
    assert listed["archive_blocked_reason"] is None
    assert by_id[str(first.id)]["read_only_reason"] == "VERSAO_NAO_MAIS_RECENTE"


def test_a_version_in_use_of_a_unit_cannot_be_deleted_and_its_table_cannot_be_archived(
    client, docente, scoring_tables, reference, uow_factory
):
    fasi = reference["FASI"]
    table, [first, second] = synthetic_table(
        uow_factory, "Tabela Sintética Em Uso", [date(2020, 1, 1), date(2021, 1, 1)], [fasi.id]
    )
    with uow_factory() as uow:
        uow.scoring_tables.set_unit_default(fasi.id, second.id)
        uow.commit()

    listed = table_json(client, table)
    by_id = {v["id"]: v for v in listed["versions"]}

    assert reasons(by_id[str(second.id)]) == (None, "VERSAO_EM_USO_DE_UNIDADE")
    assert by_id[str(first.id)]["delete_blocked_reason"] is None
    assert listed["archive_blocked_reason"] == "TABELA_COM_VERSAO_EM_USO"
    assert listed["delete_blocked_reason"] == "VERSAO_EM_USO_DE_UNIDADE"


def test_a_superseded_version_is_read_only_and_the_one_that_replaces_it_is_not_deletable(
    client, docente, scoring_tables, uow_factory
):
    table, [old, new] = synthetic_table(
        uow_factory, "Tabela Sintética Substituída", [date(2020, 1, 1), date(2020, 1, 1)]
    )
    with uow_factory() as uow:
        uow.scoring_tables.set_superseded(old.id, new.id)
        uow.commit()

    by_id = {v["id"]: v for v in table_json(client, table)["versions"]}

    assert reasons(by_id[str(old.id)]) == ("VERSAO_SUBSTITUIDA", None)
    assert reasons(by_id[str(new.id)]) == (None, "VERSAO_SUBSTITUI_OUTRA")


def test_an_older_version_is_not_the_latest_but_the_latest_is_free(
    client, docente, scoring_tables, uow_factory
):
    table, [older, latest] = synthetic_table(
        uow_factory, "Tabela Sintética Em Série", [date(2020, 1, 1), date(2022, 1, 1)]
    )

    listed = table_json(client, table)
    by_id = {v["id"]: v for v in listed["versions"]}

    assert reasons(by_id[str(older.id)]) == ("VERSAO_NAO_MAIS_RECENTE", None)
    assert reasons(by_id[str(latest.id)]) == (None, None)  # a free version: null in both
    assert listed["archive_blocked_reason"] is None
    assert listed["delete_blocked_reason"] is None


def test_a_version_whose_later_version_is_superseded_is_still_not_the_latest(
    client, docente, scoring_tables, uow_factory
):
    # The 409 of the edit counts every later version, superseded ones included (GTAB-19).
    table, [elsewhere, middle, later] = synthetic_table(
        uow_factory,
        "Tabela Sintética Sucessora Substituída",
        [date(2019, 6, 1), date(2020, 1, 1), date(2022, 1, 1)],
    )
    with uow_factory() as uow:
        uow.scoring_tables.set_superseded(later.id, elsewhere.id)
        uow.commit()

    by_id = {v["id"]: v for v in table_json(client, table)["versions"]}

    assert by_id[str(middle.id)]["read_only_reason"] == "VERSAO_NAO_MAIS_RECENTE"
    assert by_id[str(later.id)]["read_only_reason"] == "VERSAO_SUBSTITUIDA"


def test_every_version_and_the_table_of_the_official_table_are_protected_from_deletion(
    client, docente, scoring_tables
):
    official = tables_by_name(client)[OFFICIAL_NAME]

    assert official["delete_blocked_reason"] == "TABELA_OFICIAL_PROTEGIDA"
    assert {v["delete_blocked_reason"] for v in official["versions"]} == {
        "TABELA_OFICIAL_PROTEGIDA"
    }
    assert official["archive_blocked_reason"] is None  # it can be archived
    assert [v["read_only_reason"] for v in official["versions"]] == [None]


def test_the_only_version_of_a_table_cannot_be_deleted_alone(
    client, docente, scoring_tables
):
    other = tables_by_name(client)[OTHER_NAME]

    [version] = other["versions"]
    assert version["delete_blocked_reason"] == "ULTIMA_VERSAO_DA_TABELA"
    assert version["read_only_reason"] is None
    assert other["delete_blocked_reason"] is None  # the way out: delete the table


def test_the_routes_that_list_one_table_or_one_version_carry_the_same_reasons(
    client, docente, scoring_tables
):
    official = tables_by_name(client)[OFFICIAL_NAME]
    [listed] = official["versions"]

    by_table = client.get(f"/api/scoring-tables/{official['id']}/versions").json()
    one = version_detail(client, scoring_tables, "OFICIAL")

    assert by_table == official["versions"]
    assert (one["read_only_reason"], one["delete_blocked_reason"]) == reasons(listed)
