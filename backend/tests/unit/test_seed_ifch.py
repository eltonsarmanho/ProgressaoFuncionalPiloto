"""TAB-03, TAB-06: IFCH scoring table seed data against the official PDF."""

import json
from decimal import Decimal
from pathlib import Path

import pytest

SEED = Path(__file__).resolve().parents[2] / "app/infrastructure/database/seed_data/ifch.json"
COUNTS = [3, 16, 12, 7, 6, 14, 11, 66]
# Group sums transcribed from Modelos/TABELA-DE-PONTUACAO-DO-IFCH.pdf and checked against it.
SUMS = {2: 189, 3: 68, 4: 45, 5: 90, 6: 334, 7: 244, 8: 907}


@pytest.fixture(scope="module")
def data():
    return json.loads(SEED.read_text(encoding="utf-8"))


def criterion(data, group, item):
    found = next(g for g in data["groups"] if g["number"] == group)
    return next(c for c in found["criteria"] if c["item_number"] == item)


def test_criteria_count_per_group(data):
    assert [g["number"] for g in data["groups"]] == list(range(1, 9))
    assert [len(g["criteria"]) for g in data["groups"]] == COUNTS


def test_item_numbers_are_sequential_per_group(data):
    for g in data["groups"]:
        assert [c["item_number"] for c in g["criteria"]] == list(range(1, len(g["criteria"]) + 1))


def test_points_sum_per_group_matches_the_pdf(data):
    sums = {
        g["number"]: sum(Decimal(str(c["unit_points"])) for c in g["criteria"])
        for g in data["groups"]
        if g["number"] > 1
    }
    assert sums == {g: Decimal(v) for g, v in SUMS.items()}


@pytest.mark.parametrize(
    "group,item,points",
    [(2, 2, 30), (3, 2, 8), (4, 4, 2), (6, 10, 7), (7, 10, 1), (8, 1, 50)],
)
def test_reference_items(data, group, item, points):
    assert Decimal(str(criterion(data, group, item)["unit_points"])) == points


def test_group_one_does_not_count_and_item_three_is_capped_at_10(data):
    group1 = data["groups"][0]
    assert group1["counts_in_total"] is False
    assert all(g["counts_in_total"] for g in data["groups"][1:])
    first, second, third = group1["criteria"]
    assert (first["mode"], first["unit_points"]) == ("VALOR_INFORMADO", None)
    assert (second["mode"], second["unit_points"]) == ("VALOR_INFORMADO", None)
    assert (third["mode"], third["max_points"]) == ("VALOR_INFORMADO", 10)
    assert third["review_note"]


def test_hour_block_items(data):
    blocks = {
        (g["number"], c["item_number"]): (c["hours_per_block"], c["unit_points"])
        for g in data["groups"]
        for c in g["criteria"]
        if c["mode"] == "POR_BLOCO_DE_HORAS"
    }
    assert blocks == {
        (4, 3): (20, 10),
        (4, 4): (3, 2),
        (4, 5): (3, 3),
        (4, 6): (15, 5),
        (4, 7): (3, 2),
        (7, 11): (30, 1),
    }


def test_version_metadata(data):
    assert data["status"] == "OFICIAL"
    assert data["valid_from"] == "2015-03-24"
    assert data["norm_reference"] == (
        "Tabela de Pontuação do IFCH em complementação ao Anexo I da Res. 4.644/2015-CONSEPE"
    )
    assert data["minimums"]["by_current_class"] == {"A": 60, "B": 80, "C": 100, "D": 120}
    assert data["minimums"]["norm_reference"] == "Res. 4.644/2015-CONSEPE, art. 12"
