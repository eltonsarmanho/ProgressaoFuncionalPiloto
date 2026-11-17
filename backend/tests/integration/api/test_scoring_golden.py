"""CALC-14, CALC-13, SEL-06, VERIF-11: real case FASI 2022-2024 end to end through the API.

Expected values come from the filled FASI table (Assumptions of spec.md): subtotals
92, 120, 15, 95, 0, 30, 6, 56 and total 414, with the Group I points as informed.
"""

from datetime import date
from decimal import Decimal
from uuid import UUID

import pytest

from app.application.use_cases.scoring import ActivityData
from app.domain.entities.activity import ActivitySource
from app.domain.entities.user import Role
from tests.integration.api.factories import FASI_2022_2024

EXPECTED_SUBTOTALS = ["92.00", "120.00", "15.00", "95.00", "0.00", "30.00", "6.00", "56.00"]
GROUP_ONE_POINTS = ["24.00", "24.00", "24.00", "20.00"]


@pytest.fixture
def case(client, act_as, scoring_tables, reference):
    actor, headers = act_as("admin@ufpa.br", Role.ADMIN)
    professor = client.post(
        "/api/professors",
        json={
            "full_name": "Maria Docente da Silva",
            "siape": "1234567",
            "titration": "DOUTORADO",
            "position": "Professor do Magistério Superior",
            "career": "MAGISTERIO_SUPERIOR",
            "unit_id": str(reference["FASI"].id),
            "faculty": "Faculdade de Sistemas de Informação",
            "campus": "Campus Universitário do Tocantins/Cametá",
            "work_regime": "DE",
        },
        headers=headers,
    )
    assert professor.status_code == 201, professor.text
    payload = {**FASI_2022_2024, "professor_id": professor.json()["id"]}
    payload["unit_id"] = str(reference["FASI"].id)
    process = client.post("/api/processes", json=payload, headers=headers)
    assert process.status_code == 201, process.text
    process = process.json()
    chosen = client.put(
        f"/api/processes/{process['id']}/scoring/table",
        json={"version_id": str(scoring_tables["FASI"].id)},
        headers=headers,
    )
    assert chosen.status_code == 200, chosen.text
    return {"actor": actor, "headers": headers, "process": process, "client": client}


def post(case, **body):
    url = f"/api/processes/{case['process']['id']}/activities"
    response = case["client"].post(url, json=body, headers=case["headers"])
    assert response.status_code == 201, response.text
    return response.json()


def add_real_case(case):
    """The activities of the filled table, all dated inside 2022-11-23..2024-11-23."""
    semesters = [("2023.1", "2023-03-06"), ("2023.2", "2023-08-07"),
                 ("2023.3", "2023-12-04"), ("2023.4", "2024-03-04")]  # fmt: skip
    for (period, day), points in zip(semesters, (24, 24, 24, 20), strict=True):
        post(
            case, title=f"Cálculo Computacional II {period}", group_number=1, event_date=day,
            academic_period=period, level="GRADUACAO", horas=68, points_override=points,
            justificativa="Pontos declarados na tabela preenchida", evidence_note="Declaração",
        )  # fmt: skip
    counts = [(2, 7, 4), (2, 8, 4), (2, 12, 4), (4, 1, 4), (7, 10, 2)]
    for group, item, times in counts:
        for n in range(1, times + 1):
            post(
                case, title=f"Item {group}.{item} número {n}", group_number=group,
                item_number=item, quantidade=1, event_date=f"2023-0{n + 3}-15",
                evidence_note="Declaração",
            )  # fmt: skip
    for group, item in [(3, 2), (3, 3), (6, 6), (8, 11), (8, 12), (8, 13), (8, 66)]:
        post(
            case, title=f"Item {group}.{item}", group_number=group, item_number=item,
            quantidade=1, event_date="2024-02-20", evidence_note="Declaração",
        )  # fmt: skip
    post(
        case, title="Curso de extensão ministrado", group_number=4, item_number=4, horas=21,
        event_date="2024-05-10", evidence_note="Certificado",
    )  # fmt: skip


def score(case):
    response = case["client"].get(f"/api/processes/{case['process']['id']}/scoring")
    assert response.status_code == 200, response.text
    return response.json()


@pytest.fixture
def real_case(case):
    add_real_case(case)
    return case


def test_subtotals_and_total_match_the_filled_table(real_case):
    body = score(real_case)

    assert [s["group_number"] for s in body["subtotals"]] == list(range(1, 9))
    assert [s["subtotal"] for s in body["subtotals"]] == EXPECTED_SUBTOTALS
    assert body["total"] == "414.00"
    assert body["potential_total"] == "0.00"
    assert body["counters"] == {
        "activities": 30, "with_evidence": 30, "pending": 0, "not_scored": 0, "with_alerts": 4,
    }  # fmt: skip


def test_group_one_share_minimum_and_pending_table_alert(real_case):
    body = score(real_case)

    assert body["group1_percent"] == "22.22"
    assert body["minimum"] == {"status": "ATINGE", "minimum": "100.00", "total": "414.00"}
    alerts = {a["code"]: a for a in body["alerts"]}
    assert alerts["TABELA_PENDENTE_VALIDACAO"]["severity"] == "REQUER_ANALISE_NORMATIVA"
    assert alerts["TABELA_PENDENTE_VALIDACAO"]["norm_reference"].startswith(
        "Tabela preenchida FASI"
    )
    assert "SEM_EXTENSAO_OU_PESQUISA" not in alerts
    assert "MINIMO_NAO_DEFINIDO" not in alerts


def test_rows_carry_formula_points_and_the_manual_adjustment_alert(real_case):
    rows = score(real_case)["rows"]
    group_one = [r for r in rows if r["group_number"] == 1]
    block_row = next(r for r in rows if (r["group_number"], r["item_number"]) == (4, 4))

    assert [r["points"] for r in group_one] == GROUP_ONE_POINTS
    assert {r["item_number"] for r in group_one} == {1}
    assert all(
        [a["code"] for a in r["alerts"]] == ["PONTOS_AJUSTADOS_MANUALMENTE"] for r in group_one
    )
    assert (block_row["points"], block_row["effective_quantity"]) == ("35.00", "7.00")
    assert block_row["formula_text"] == "21 h ÷ 3 h = 7 blocos × 5"
    assert {r["status"] for r in rows} == {"PONTUADA"}


def test_extra_activities_stay_out_of_the_total(real_case):
    case = real_case
    before = score(case)
    post(
        case, title="Orientação anterior ao interstício", group_number=2, item_number=7,
        quantidade=1, event_date="2022-06", evidence_note="Declaração",
    )  # fmt: skip
    post(
        case, title="  ITEM 2.7 número 1 ", group_number=2, item_number=7, quantidade=1,
        event_date="2023-04-15", evidence_note="Declaração",
    )  # fmt: skip
    container = case["client"].app.state.container
    pending = container.create_activity.execute(
        case["actor"],
        UUID(case["process"]["id"]),
        ActivityData(
            title="Sugestão da IA", group_number=2, item_number=7, quantity=Decimal(1),
            event_date=date(2023, 6, 6),
        ),
        source=ActivitySource.SUGERIDA_IA,
    )  # fmt: skip

    after = score(case)

    assert [s["subtotal"] for s in after["subtotals"]] == EXPECTED_SUBTOTALS
    assert after["total"] == "414.00"
    assert after["group1_percent"] == "22.22"
    assert after["potential_total"] == "10.00"
    by_title = {r["title"]: r for r in after["rows"]}
    old = by_title["Orientação anterior ao interstício"]
    assert (old["status"], old["reasons"], old["points"]) == (
        "NAO_PONTUADA", ["FORA_DO_INTERSTICIO"], "0.00",
    )  # fmt: skip
    duplicate = by_title["ITEM 2.7 número 1"]
    assert (duplicate["status"], duplicate["reasons"]) == ("NAO_PONTUADA", ["DUPLICIDADE"])
    waiting = by_title["Sugestão da IA"]
    assert (waiting["status"], waiting["points"], waiting["activity_status"]) == (
        "POTENCIAL", "10.00", "AGUARDANDO_REVISAO",
    )  # fmt: skip
    assert pending.status.value == "AGUARDANDO_REVISAO"
    assert after["counters"]["activities"] == before["counters"]["activities"] + 3
    assert after["counters"]["pending"] == 1
    assert after["counters"]["not_scored"] == 2
    month_activity = next(
        a for a in case["client"].get(f"/api/processes/{case['process']['id']}/activities").json()
        if a["title"] == "Orientação anterior ao interstício"
    )  # fmt: skip
    assert month_activity["event_date"] == "2022-06"
    assert month_activity["period_precision"] == "MONTH"


def test_the_result_is_the_same_on_every_query(real_case):
    assert score(real_case) == score(real_case)
