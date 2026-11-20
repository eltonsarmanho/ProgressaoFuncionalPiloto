"""VER-02: the snapshot saved with each generated version."""

import json
from dataclasses import replace
from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.entities.generated import DocumentKind
from app.domain.rules.generation_snapshot import build_snapshot
from tests.unit.domain.scenario_211 import (
    INTERSTICE,
    activity,
    official_like_table,
    scenario_result,
)

LAYOUT = {"plan_hash": "ab" * 32, "entries": []}
REPORT = {"sections": [{"key": "1.1", "entries": []}]}
TEMPLATE = {"id": "ufpa-modelo-2", "version": 1}


def snapshot(kind=DocumentKind.TABELA, activities=None, version=None, **overrides):
    version = version or replace(official_like_table(), id=uuid4())
    version, activities, result = scenario_result(activities, version)
    options = {
        "excluded": {"pendentes": 2, "sem_enquadramento": 1},
        "alerts": ["SEM_COMPROVANTE"],
        "template": TEMPLATE,
        "layout": LAYOUT,
        "report": REPORT,
    }
    options.update(overrides)
    return (
        build_snapshot(kind, version, INTERSTICE, result, activities, **options),
        version,
        activities,
        result,
    )


def test_the_table_snapshot_names_the_table_version():
    data, version, _, _ = snapshot()

    assert data["table_version"] == {
        "id": str(version.id),
        "name": "Tabela de teste 2022",
        "norm_reference": "Res. de teste, Anexo I",
    }


def test_the_snapshot_keeps_the_interstice_total_and_every_group_subtotal():
    data, _, _, _ = snapshot()

    assert data["interstice"] == {"start": "2022-11-23", "end": "2024-11-23"}
    assert data["total"] == "211.00"
    assert data["subtotals"] == {
        "1": "0.00", "2": "52.00", "3": "7.00", "4": "62.00",
        "5": "0.00", "6": "30.00", "7": "4.00", "8": "56.00",
    }  # fmt: skip


def test_the_snapshot_keeps_the_pit_hours_by_period_and_in_total():
    data, _, _, _ = snapshot()

    assert data["pit_hours"] == {
        "2023.1": "24.00", "2023.2": "24.00", "2023.3": "24.00", "2023.4": "20.00",
    }  # fmt: skip
    assert data["pit_total_hours"] == "92.00"


def test_the_snapshot_lists_each_activity_with_group_item_quantity_points_and_status():
    a = activity(2, 7, "2", title="Orientação de TCC")

    data, _, _, _ = snapshot(activities=[a])

    assert data["activities"] == [
        {
            "id": str(a.id),
            "group": 2,
            "item": 7,
            "quantity": "2.00",
            "points": "32.00",
            "status": "PONTUADA",
        }
    ]


def test_an_activity_that_does_not_score_has_no_quantity_and_zero_points():
    # SEG-01: outside the interstice is not valid and has no row; an item the table does not
    # have is the case left of an activity that does not score
    late = activity(2, 99)

    data, _, _, _ = snapshot(activities=[late])

    assert data["activities"][0]["quantity"] is None
    assert (data["activities"][0]["points"], data["activities"][0]["status"]) == (
        "0.00",
        "NAO_PONTUADA",
    )


def test_only_the_listed_activities_are_in_the_snapshot():
    kept, left_out = activity(3, 2), activity(3, 2)
    version, activities, result = scenario_result([kept, left_out])

    data = build_snapshot(
        DocumentKind.TABELA, version, INTERSTICE, result, [kept], excluded={}, alerts=[]
    )

    assert [x["id"] for x in data["activities"]] == [str(kept.id)]


def test_the_excluded_counts_by_reason_and_the_alert_codes_are_kept():
    data, _, _, _ = snapshot()

    assert data["excluded"] == {"pendentes": 2, "sem_enquadramento": 1}
    assert data["alerts"] == ["SEM_COMPROVANTE"]


@pytest.mark.parametrize(
    ("kind", "present", "absent"),
    [
        (DocumentKind.TABELA, "table_version", "layout"),
        (DocumentKind.TABELA, "table_version", "report"),
        (DocumentKind.COMPROVANTE, "layout", "report"),
        (DocumentKind.RELATORIO, "report", "layout"),
    ],
)
def test_layout_and_report_only_appear_in_their_own_kinds(kind, present, absent):
    data, _, _, _ = snapshot(kind)

    assert present in data
    assert absent not in data


def test_the_layout_and_the_report_are_the_ones_given():
    comprovante, _, _, _ = snapshot(DocumentKind.COMPROVANTE)
    report, _, _, _ = snapshot(DocumentKind.RELATORIO)

    assert comprovante["layout"] == LAYOUT
    assert report["report"] == REPORT


def test_the_template_is_only_in_the_report_snapshot():
    report, _, _, _ = snapshot(DocumentKind.RELATORIO)
    table, _, _, _ = snapshot(DocumentKind.TABELA)
    voucher, _, _, _ = snapshot(DocumentKind.COMPROVANTE)

    assert report["template"] == TEMPLATE
    assert "template" not in table
    assert "template" not in voucher


@pytest.mark.parametrize("kind", list(DocumentKind))
def test_the_snapshot_survives_a_json_round_trip_unchanged(kind):
    data, _, _, _ = snapshot(kind)

    assert json.loads(json.dumps(data)) == data


def test_the_same_input_gives_the_same_output():
    version = replace(official_like_table(), id=uuid4())
    version, activities, result = scenario_result(None, version)

    def build():
        return build_snapshot(
            DocumentKind.TABELA, version, INTERSTICE, result, activities,
            excluded={"b": 1, "a": 2}, alerts=["X"], layout=LAYOUT,
        )  # fmt: skip

    assert json.dumps(build()) == json.dumps(build())
    assert list(build()["excluded"]) == ["a", "b"]


def test_a_table_version_without_persistence_identity_has_no_id():
    data, _, _, _ = snapshot(version=official_like_table())

    assert data["table_version"]["id"] is None


def test_a_total_with_decimals_keeps_two_places():
    base = official_like_table()
    three = base.groups[2]
    half_point = replace(three.criteria[0], unit_points=Decimal("7.5"))
    version = replace(
        base, groups=(*base.groups[:2], replace(three, criteria=(half_point,)), *base.groups[3:])
    )

    data, _, _, _ = snapshot(activities=[activity(3, 2, "1")], version=version)

    assert data["total"] == "7.50"
