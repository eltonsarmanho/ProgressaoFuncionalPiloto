"""TAB-04, TAB-05, TAB-07: FASI scoring table seed data against the filled table."""

import json
from decimal import Decimal
from pathlib import Path

import pytest

DIR = Path(__file__).resolve().parents[2] / "app/infrastructure/database/seed_data"
COUNTS = [3, 16, 12, 7, 6, 14, 11, 66]
DIVERGENT_II_TO_VII = {
    (2, 9), (2, 12), (2, 16), (3, 2), (3, 6), (3, 7), (3, 8), (3, 9), (4, 2), (4, 4), (4, 5),
    (4, 7), (6, 10), (6, 11), (6, 12), (7, 9), (7, 10),
}  # fmt: skip
GROUP_VIII_ANOMALIES = {(8, 5), (8, 6), (8, 7), (8, 38), (8, 39)}


@pytest.fixture(scope="module")
def data():
    return json.loads((DIR / "fasi.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def ifch():
    return json.loads((DIR / "ifch.json").read_text(encoding="utf-8"))


def criteria(data):
    return {(g["number"], c["item_number"]): c for g in data["groups"] for c in g["criteria"]}


def test_criteria_count_per_group(data):
    assert [len(g["criteria"]) for g in data["groups"]] == COUNTS


def test_flagged_items_are_exactly_the_divergences(data):
    flagged = {key for key, c in criteria(data).items() if c["review_note"]}
    assert flagged == DIVERGENT_II_TO_VII | GROUP_VIII_ANOMALIES


def test_only_flagged_items_differ_from_ifch_in_groups_ii_to_vii(data, ifch):
    mine, theirs = criteria(data), criteria(ifch)
    differing = {
        key
        for key in mine
        if 2 <= key[0] <= 7 and mine[key]["unit_points"] != theirs[key]["unit_points"]
    }
    assert differing == DIVERGENT_II_TO_VII


@pytest.mark.parametrize(
    "key,points",
    [
        ((2, 7), 10), ((2, 8), 10), ((2, 12), 10), ((3, 2), 10), ((3, 3), 5), ((4, 1), 15),
        ((4, 4), 5), ((6, 6), 30), ((7, 10), 3), ((8, 11), 25), ((8, 12), 20), ((8, 13), 6),
        ((8, 66), 5),
    ],
)  # fmt: skip
def test_real_case_points(data, key, points):
    assert Decimal(str(criteria(data)[key]["unit_points"])) == points


@pytest.mark.parametrize(
    "key,points", [((8, 5), 20), ((8, 6), 10), ((8, 7), 10), ((8, 38), 30), ((8, 39), 15)]
)
def test_group_viii_anomaly_values(data, key, points):
    assert Decimal(str(criteria(data)[key]["unit_points"])) == points


def test_ifch_difference_is_described_in_the_note(data):
    notes = criteria(data)
    assert "atribui 5 pontos" in notes[(2, 9)]["review_note"]
    assert "do IFCH, 2." in notes[(2, 9)]["review_note"]
    assert "por turma/ano" == notes[(2, 12)]["unit_label"]
    assert "20 horas" in notes[(4, 4)]["review_note"]
    assert notes[(4, 4)]["hours_per_block"] == 3
    assert "IFCH" in notes[(8, 7)]["review_note"]


def test_group_one_counts_and_uses_weekly_load(data):
    group1 = data["groups"][0]
    assert group1["counts_in_total"] is True
    first, second, third = group1["criteria"]
    assert (first["mode"], first["weeks_per_semester"], Decimal(str(first["prep_ratio"]))) == (
        "CARGA_SEMANAL", 17, 1,
    )  # fmt: skip
    assert (second["mode"], second["weeks_per_semester"], Decimal(str(second["prep_ratio"]))) == (
        "CARGA_SEMANAL", 17, 2,
    )  # fmt: skip
    assert (third["mode"], third["max_points"]) == ("VALOR_INFORMADO", 10)


def test_version_metadata(data):
    assert data["status"] == "PENDENTE_VALIDACAO"
    assert data["valid_from"] == "2022-11-23"
    assert data["norm_reference"] == (
        "Tabela preenchida FASI/Campus Cametá, interstício 2022–2024 (sem norma localizada)"
    )
    assert "Créditos de doutorado" in data["notes"]
    assert criteria(data)[(8, 5)]["description"].startswith("Tradução de livro")
