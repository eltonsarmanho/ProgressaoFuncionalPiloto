"""PIT-02, GI-06, GI-07, GRES-04, GRES-09: GET /processes/{id}/scoring exposes PIT hours per row,
per period and in total, with the term, the level and the flag of the total on every row: on the
previous version of the official table (group I outside the total) and on the seeded one."""

import pytest

from app.domain.entities.user import Role
from app.infrastructure.database.seed import seed_scoring_tables
from tests.integration.api.factories import add_professor, process_payload
from tests.support.scoring_variants import add_legacy_ufpa_version


def scored_process(client, act_as, reference, uow_factory, previous: bool):
    """A FASI process with three group I offers and one II.7, on the previous version of the
    official table (group I outside the total, GI-06) or on the seeded one (group I inside)."""
    seed_scoring_tables(uow_factory())
    _, headers = act_as("admin@ufpa.br", Role.ADMIN)
    with uow_factory() as uow:
        table = next(
            t for t in uow.scoring_tables.list_tables() if t.name == "Tabela de Pontuação da UFPA"
        )
        version = uow.scoring_tables.list_versions(table.id)[0]
        if previous:
            version = add_legacy_ufpa_version(uow, version)
        uow.commit()
    professor = add_professor(uow_factory, reference["FASI"])
    process = client.post("/api/processes", json=process_payload(professor), headers=headers)
    assert process.status_code == 201, process.text
    process = process.json()
    chosen = client.put(
        f"/api/processes/{process['id']}/scoring/table",
        json={"version_id": str(version.id)},
        headers=headers,
    )
    assert chosen.status_code == 200, chosen.text
    base = {"event_date": "2023-05-10", "evidence_note": "Declaração"}
    activities = [
        {"title": "Disciplina A", "group_number": 1, "academic_period": "2023.1",
         "level": "GRADUACAO", "horas": 68},
        {"title": "Disciplina B", "group_number": 1, "academic_period": "2023.1",
         "level": "GRADUACAO", "horas": 34},
        {"title": "Disciplina C", "group_number": 1, "academic_period": "2023.2",
         "level": "POS_GRADUACAO", "horas": 68},
        {"title": "Orientação", "group_number": 2, "item_number": 7, "quantidade": 1},
    ]  # fmt: skip
    for body in activities:
        response = client.post(
            f"/api/processes/{process['id']}/activities", json={**base, **body}, headers=headers
        )
        assert response.status_code == 201, response.text
    return client.get(f"/api/processes/{process['id']}/scoring").json()


@pytest.fixture
def scored(client, act_as, reference, uow_factory):
    return scored_process(client, act_as, reference, uow_factory, previous=True)


@pytest.fixture
def scored_new(client, act_as, reference, uow_factory):
    return scored_process(client, act_as, reference, uow_factory, previous=False)


def test_group_one_rows_carry_pit_hours_with_two_places_and_zero_points(scored):
    group_one = [r for r in scored["rows"] if r["group_number"] == 1]

    assert sorted(r["pit_hours"] for r in group_one) == ["12.00", "4.00", "8.00"]
    assert {r["points"] for r in group_one} == {"0.00"}


def test_rows_outside_group_one_have_no_pit_hours(scored):
    other = [r for r in scored["rows"] if r["group_number"] == 2]

    assert [(r["pit_hours"], r["points"]) for r in other] == [(None, "5.00")]


def test_hours_are_summed_per_academic_period_and_in_total(scored):
    assert scored["group1_hours_by_period"] == {"2023.1": "12.00", "2023.2": "12.00"}
    assert scored["group1_total_hours"] == "24.00"


def test_group_one_stays_out_of_the_total_and_the_subtotals(scored):
    subtotals = {s["group_number"]: s["subtotal"] for s in scored["subtotals"]}

    assert subtotals[1] == "0.00"
    assert subtotals[2] == "5.00"
    assert scored["total"] == "5.00"


def test_previous_version_rows_carry_term_level_and_the_outside_total_flag(scored):
    # GRES-09: the hours are shown and the row scores 0
    group_one = {r["title"]: r for r in scored["rows"] if r["group_number"] == 1}

    flags = {
        t: (r["academic_period"], r["level"], r["outside_total"]) for t, r in group_one.items()
    }
    assert flags == {
        "Disciplina A": ("2023.1", "GRADUACAO", True),
        "Disciplina B": ("2023.1", "GRADUACAO", True),
        "Disciplina C": ("2023.2", "POS_GRADUACAO", True),
    }
    assert {r["points"] for r in group_one.values()} == {"0.00"}


def test_new_version_rows_carry_term_level_and_the_hours_as_points(scored_new):
    # GI-07, GRES-04: the offer counts in the total and its hours are its points
    group_one = {r["title"]: r for r in scored_new["rows"] if r["group_number"] == 1}

    flags = {
        t: (r["academic_period"], r["level"], r["outside_total"]) for t, r in group_one.items()
    }
    assert flags == {
        "Disciplina A": ("2023.1", "GRADUACAO", False),
        "Disciplina B": ("2023.1", "GRADUACAO", False),
        "Disciplina C": ("2023.2", "POS_GRADUACAO", False),
    }
    assert {t: (r["pit_hours"], r["points"]) for t, r in group_one.items()} == {
        "Disciplina A": ("8.00", "8.00"),
        "Disciplina B": ("4.00", "4.00"),
        "Disciplina C": ("12.00", "12.00"),
    }
    assert scored_new["total"] == "29.00"


@pytest.fixture(params=[True, False], ids=["previous", "new"])
def scored_either(request, client, act_as, reference, uow_factory):
    return scored_process(client, act_as, reference, uow_factory, previous=request.param)


def test_rows_outside_group_one_have_no_term_no_level_and_count_in_the_total(scored_either):
    [other] = [r for r in scored_either["rows"] if r["group_number"] == 2]

    assert (other["academic_period"], other["level"], other["outside_total"]) == (None, None, False)


@pytest.fixture
def official_copy(client, act_as, reference, uow_factory):
    """(headers, version id) of an unused copy of the official table."""
    seed_scoring_tables(uow_factory())
    _, headers = act_as("admin@ufpa.br", Role.ADMIN)
    official = next(
        t for t in client.get("/api/scoring-tables").json() if t["name"].endswith("da UFPA")
    )
    url = f"/api/scoring-tables/{official['id']}/duplicate"
    copy = client.post(url, json={"new_name": "Cópia"}, headers=headers)
    assert copy.status_code == 201, copy.text
    return headers, copy.json()["versions"][0]["id"]


def test_version_criteria_expose_min_hours_with_two_places(client, official_copy):
    _, version_id = official_copy

    version = client.get(f"/api/scoring-versions/{version_id}").json()
    group_four = {c["item_number"]: c for g in version["groups"] if g["number"] == 4
                  for c in g["criteria"]}  # fmt: skip

    assert [group_four[i]["min_hours"] for i in (3, 4, 5)] == ["20.00"] * 3
    assert group_four[6]["min_hours"] is None


def test_criterion_update_route_changes_min_hours(client, official_copy):
    headers, version_id = official_copy

    response = client.put(
        f"/api/scoring-versions/{version_id}/criteria/4/6",
        json={"change_reference": "Res. 7.000/2026", "changes": {"min_hours": "8"}},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["min_hours"] == "8.00"
