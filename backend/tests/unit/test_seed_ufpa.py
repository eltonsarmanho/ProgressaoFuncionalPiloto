"""OFI-01..OFI-06, OFI-10, GI-07, GI-12: official UFPA scoring table seed data (ufpa.json)."""

import json
from decimal import Decimal
from pathlib import Path

import pytest

DIR = Path(__file__).resolve().parents[2] / "app/infrastructure/database/seed_data"
COUNTS = [2, 16, 9, 6, 5, 14, 11, 37]
# groups II to VIII; GI-12: VI.14 is 3 points a year, so group VI is 329 (was 332 with 6)
GROUP_SUMS = [158, 44, 40, 75, 329, 258, 407]
DECIDED_BY_USER = {(2, 10): 10, (6, 14): 3, (8, 4): 15, (8, 8): 15, (8, 12): 2}


@pytest.fixture(scope="module")
def data():
    return json.loads((DIR / "ufpa.json").read_text(encoding="utf-8"))


def criteria(data):
    return {(g["number"], c["item_number"]): c for g in data["groups"] for c in g["criteria"]}


def test_criteria_count_per_group(data):
    assert [g["number"] for g in data["groups"]] == list(range(1, 9))
    assert [len(g["criteria"]) for g in data["groups"]] == COUNTS


def test_item_numbers_are_sequential_from_one(data):
    for group in data["groups"]:
        numbers = [c["item_number"] for c in group["criteria"]]
        assert numbers == list(range(1, len(numbers) + 1))


def test_group_sums_ii_to_viii_and_grand_total(data):
    sums = [sum(Decimal(str(c["unit_points"])) for c in g["criteria"]) for g in data["groups"][1:]]
    assert sums == GROUP_SUMS
    assert sum(sums) == 1311  # GI-12: was 1314 with VI.14 = 6


@pytest.mark.parametrize("key,points", sorted(DECIDED_BY_USER.items()))
def test_values_decided_by_the_user(data, key, points):
    assert Decimal(str(criteria(data)[key]["unit_points"])) == points


@pytest.mark.parametrize("key", sorted(DECIDED_BY_USER))
def test_decided_items_record_the_spreadsheet_divergence(data, key):
    note = criteria(data)[key]["review_note"]
    assert "decisão do usuário" in note
    assert "planilha" in note


@pytest.mark.parametrize(
    "key,points",
    [((2, 7), 5), ((3, 2), 5), ((3, 4), 2), ((4, 1), 15), ((8, 9), 25), ((8, 24), 10),
     ((8, 33), 15)],
)  # fmt: skip
def test_reference_items_follow_the_spreadsheet(data, key, points):
    assert Decimal(str(criteria(data)[key]["unit_points"])) == points


@pytest.mark.parametrize("key", [(4, 3), (4, 4), (4, 5)])
def test_course_items_require_twenty_hours(data, key):
    assert Decimal(str(criteria(data)[key]["min_hours"])) == 20


def test_only_the_three_course_items_have_a_minimum(data):
    with_minimum = {key for key, c in criteria(data).items() if c["min_hours"] is not None}
    assert with_minimum == {(4, 3), (4, 4), (4, 5)}


def test_internship_scores_one_point_per_thirty_hours(data):
    item = criteria(data)[(7, 11)]
    assert item["mode"] == "POR_BLOCO_DE_HORAS"
    assert Decimal(str(item["hours_per_block"])) == 30
    assert Decimal(str(item["unit_points"])) == 1


def test_every_other_group_ii_to_viii_item_is_per_unit(data):
    modes = {key: c["mode"] for key, c in criteria(data).items() if key[0] >= 2}
    assert {k for k, m in modes.items() if m != "POR_UNIDADE"} == {(7, 11)}


def test_ministries_leave_item_has_no_points_and_keeps_the_text(data):
    item = criteria(data)[(8, 37)]
    assert Decimal(str(item["unit_points"])) == 0
    assert item["description"].startswith("Afastamento de docente")
    assert "Ministérios da Educação" in item["description"]


def test_group_one_is_pit_hours_counting_in_the_total(data):
    # GI-07: was "outside the total" (PIT-01); the new version counts group I, at 1 point an hour.
    group1 = data["groups"][0]
    assert group1["counts_in_total"] is True
    first, second = group1["criteria"]
    assert (first["mode"], first["weeks_per_semester"], Decimal(str(first["prep_ratio"]))) == (
        "CARGA_SEMANAL", 17, 1,
    )  # fmt: skip
    assert (second["mode"], second["weeks_per_semester"], Decimal(str(second["prep_ratio"]))) == (
        "CARGA_SEMANAL", 17, 2,
    )  # fmt: skip
    assert first["description"].startswith("Aulas Efetivas em Curso de Graduação")
    assert second["description"].startswith("Aulas Efetivas em Curso de Pós-Graduação")


def test_group_one_has_no_points_ceiling_in_the_group_nor_in_its_two_items(data):
    # S4: GI-03 ("hours equal the points") only holds while nothing caps group I.
    group1 = data["groups"][0]
    assert group1["max_points"] is None
    assert [c["max_points"] for c in group1["criteria"]] == [None, None]


def test_groups_ii_to_viii_count_in_the_total(data):
    assert all(g["counts_in_total"] is True for g in data["groups"][1:])


def test_table_and_version_metadata(data):
    assert data["table_name"] == "Tabela de Pontuação da UFPA"
    assert data["version_name"] == "Tabela oficial de pontuação UFPA, Grupo I no total"
    assert data["status"] == "OFICIAL"
    assert data["valid_from"] == "2015-03-24"
    assert data["valid_to"] is None
    assert data["norm_reference"] == (
        "Tabela oficial de pontuação para progressão docente da UFPA "
        "(planilha fornecida em 2026-11-17), com o Grupo I somado ao total a 1 ponto por hora "
        "de PIT por decisão do usuário em 2026-11-19"
    )


def test_the_version_names_the_one_it_supersedes(data):
    assert data["supersedes"] == "Tabela oficial de pontuação UFPA"
    assert data["supersedes"] != data["version_name"]


def test_notes_say_group_one_counts_and_vi_14_is_three_points(data):
    assert "Grupo I" in data["notes"]
    assert "entra no total" in data["notes"]
    assert "VI.14" in data["notes"] and "3 pontos por ano" in data["notes"]
    assert "não entra no total" not in data["notes"]


def test_vi_14_review_note_records_the_decision_of_2026_11_19(data):
    note = criteria(data)[(6, 14)]["review_note"]
    assert "2026-11-19" in note
    assert "3 pontos" in note


def test_minimums_by_class_with_the_resolution_reference(data):
    assert data["minimums"] == {
        "structure": "Res. 4.644/2015-CONSEPE",
        "norm_reference": "Res. 4.644/2015-CONSEPE, art. 12",
        "by_current_class": {"A": 60, "B": 80, "C": 100, "D": 120},
    }


def test_descriptions_come_from_the_spreadsheet(data):
    items = criteria(data)
    assert items[(2, 1)]["description"].startswith("Tutoria de pós-doutorado concluída")
    assert items[(8, 24)]["description"].startswith("Participação como apresentador")
    assert items[(3, 9)]["description"].startswith("Membro de banca de seleção para bolsas")
    assert all(c["description"].strip() for c in items.values())
