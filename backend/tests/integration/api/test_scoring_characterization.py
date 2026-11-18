"""TAB-01, TAB-04: the /scoring response of the 2022-2024 case, fixed before the extraction.

Characterization of the screen response (AD-006: recomputed on demand) so that extracting
compute_process_score cannot change what the screen shows. The scenario is the derived case of
test_scoring_golden (total 211); no real data.
"""

from uuid import UUID

# The fixtures and the scenario builder come from the golden-case module.
from tests.integration.api.test_scoring_golden import (  # noqa: F401, F811
    case,
    real_case,
    score,
)

TOP_LEVEL_KEYS = {
    "process_id", "chosen", "suggested", "subtotals", "total", "potential_total",
    "potential_dated", "potential_undated", "group1_percent", "group1_hours_by_period",
    "group1_total_hours", "counters", "rows", "limit_adjustments", "alerts", "minimum",
}  # fmt: skip
ROW_KEYS = {
    "activity_id", "title", "activity_status", "evidence_note", "group_number", "item_number",
    "unit_points", "effective_quantity", "formula_text", "points", "pit_hours", "status",
    "reasons", "alerts", "evidence_count",
}  # fmt: skip


def test_the_scoring_response_of_the_2022_2024_case_is_fixed(real_case):  # noqa: F811
    body = score(real_case)

    assert set(body) == TOP_LEVEL_KEYS
    assert body["process_id"] == real_case["process"]["id"]
    assert body["total"] == "211.00"
    assert [s["subtotal"] for s in body["subtotals"]] == [
        "0.00", "52.00", "7.00", "62.00", "0.00", "30.00", "4.00", "56.00",
    ]  # fmt: skip
    assert body["counters"] == {
        "activities": 38, "with_evidence": 38, "pending": 0, "not_scored": 0, "with_alerts": 0,
    }  # fmt: skip
    assert body["group1_total_hours"] == "92.00"
    assert body["limit_adjustments"] == []
    assert body["alerts"] == []
    assert body["minimum"] == {"status": "ATINGE", "minimum": "100.00", "total": "211.00"}
    assert body["chosen"]["table_name"] == "Tabela de Pontuação da UFPA"
    assert body["chosen"] == body["suggested"]


def test_every_row_keeps_its_shape_and_the_listing_order(real_case):  # noqa: F811
    rows = score(real_case)["rows"]

    assert len(rows) == 38
    assert all(set(r) == ROW_KEYS for r in rows)
    assert all(UUID(r["activity_id"]) for r in rows)
    assert [r["group_number"] for r in rows] == sorted(r["group_number"] for r in rows)
    assert {r["status"] for r in rows} == {"PONTUADA"}
    assert {r["evidence_count"] for r in rows} == {0}
    assert {r["evidence_note"] for r in rows} == {"Declaração", "Certificado"}
