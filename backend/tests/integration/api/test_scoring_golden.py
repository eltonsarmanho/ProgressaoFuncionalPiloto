"""ACE-01, PIT-01, PIT-02: cenário derivado de 2022-2024 on the official table, through the API.

The quantities of the cenário derivado (synthetic, 2022-2024) are entered on the official table
(tabela-oficial spec, Acceptance story): in this cenário derivado the subtotals II to VIII are 52,
7, 62, 0, 30, 4 and 56 and the total is 211, with PIT hours per period of 24, 24, 24 and 20 (92 in
total), group I outside the total. The total 414 came from the filled FASI table and no longer
applies; this is not a result approved in a real process.
"""

from dataclasses import replace
from datetime import date
from decimal import Decimal
from uuid import UUID

import pytest

from app.application.use_cases.scoring import ActivityData
from app.domain.entities.activity import ActivitySource, ActivityStatus, PeriodPrecision
from app.domain.entities.user import Role
from tests.integration.api.factories import FASI_2022_2024

EXPECTED_SUBTOTALS = ["0.00", "52.00", "7.00", "62.00", "0.00", "30.00", "4.00", "56.00"]
EXPECTED_HOURS_BY_PERIOD = {
    "2023.1": "24.00", "2023.2": "24.00", "2023.3": "24.00", "2023.4": "20.00",
}  # fmt: skip
PIT_HOURS = ["8.00"] * 11 + ["4.00"]


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
        json={"version_id": str(scoring_tables["OFICIAL"].id)},
        headers=headers,
    )
    assert chosen.status_code == 200, chosen.text
    return {"actor": actor, "headers": headers, "process": process, "client": client}


def post(case, **body):
    url = f"/api/processes/{case['process']['id']}/activities"
    response = case["client"].post(url, json=body, headers=case["headers"])
    assert response.status_code == 201, response.text
    return response.json()


def add_derived_case(case):
    """The activities of the cenário derivado de 2022–2024 (sintético), 211 pontos.

    All dated inside 2022-11-23..2024-11-23.
    """
    semesters = [("2023.1", "2023-03-06"), ("2023.2", "2023-08-07"),
                 ("2023.3", "2023-12-04"), ("2023.4", "2024-03-04")]  # fmt: skip
    offers = [(68, 68, 68), (68, 68, 68), (68, 68, 68), (68, 68, 34)]  # teaching hours per offer
    for (period, day), hours in zip(semesters, offers, strict=True):
        for number, offer_hours in enumerate(hours, start=1):
            post(
                case, title=f"Disciplina {number} {period}", group_number=1, event_date=day,
                academic_period=period, level="GRADUACAO", horas=offer_hours,
                evidence_note="Declaração",
            )  # fmt: skip
    counts = [(2, 7, 4), (2, 8, 4), (2, 12, 4), (4, 1, 4), (7, 10, 2)]
    for group, item, times in counts:
        for n in range(1, times + 1):
            post(
                case, title=f"Item {group}.{item} número {n}", group_number=group,
                item_number=item, quantidade=1, event_date=f"2023-0{n + 3}-15",
                evidence_note="Declaração",
            )  # fmt: skip
    for group, item in [(3, 2), (3, 3), (6, 6), (8, 9), (8, 10), (8, 11), (8, 36)]:
        post(
            case, title=f"Item {group}.{item}", group_number=group, item_number=item,
            quantidade=1, event_date="2024-02-20", evidence_note="Declaração",
        )  # fmt: skip
    post(
        case, title="Curso de extensão ministrado", group_number=4, item_number=4, quantidade=1,
        horas=21, event_date="2024-05-10", evidence_note="Certificado",
    )  # fmt: skip


def score(case):
    response = case["client"].get(f"/api/processes/{case['process']['id']}/scoring")
    assert response.status_code == 200, response.text
    return response.json()


@pytest.fixture
def derived_case(case):
    add_derived_case(case)
    return case


def test_subtotals_and_total_match_the_official_table(derived_case):
    body = score(derived_case)

    assert [s["group_number"] for s in body["subtotals"]] == list(range(1, 9))
    assert [s["subtotal"] for s in body["subtotals"]] == EXPECTED_SUBTOTALS
    assert body["total"] == "211.00"
    assert body["potential_total"] == "0.00"
    assert body["counters"] == {
        "activities": 38, "with_evidence": 38, "pending": 0, "not_scored": 0, "with_alerts": 0,
    }  # fmt: skip


def test_pit_hours_per_period_and_in_total_stay_outside_the_total(derived_case):
    body = score(derived_case)

    assert body["group1_hours_by_period"] == EXPECTED_HOURS_BY_PERIOD
    assert body["group1_total_hours"] == "92.00"
    assert body["subtotals"][0] == {"group_number": 1, "subtotal": "0.00"}
    assert body["group1_percent"] == "0.00"


def test_minimum_and_table_alerts_for_the_official_table(derived_case):
    body = score(derived_case)

    assert body["minimum"] == {"status": "ATINGE", "minimum": "100.00", "total": "211.00"}
    alerts = {a["code"]: a for a in body["alerts"]}
    assert "TABELA_PENDENTE_VALIDACAO" not in alerts
    assert "SEM_EXTENSAO_OU_PESQUISA" not in alerts
    assert "MINIMO_NAO_DEFINIDO" not in alerts


def test_rows_carry_formula_points_and_pit_hours(derived_case):
    rows = score(derived_case)["rows"]
    group_one = [r for r in rows if r["group_number"] == 1]
    course_row = next(r for r in rows if (r["group_number"], r["item_number"]) == (4, 4))

    assert [r["pit_hours"] for r in group_one] == PIT_HOURS
    assert {r["points"] for r in group_one} == {"0.00"}
    assert {r["item_number"] for r in group_one} == {1}
    assert all(r["alerts"] == [] for r in group_one)
    assert [r["pit_hours"] for r in rows if r["group_number"] != 1] == [None] * 26
    assert (course_row["points"], course_row["effective_quantity"]) == ("2.00", "1.00")
    assert course_row["formula_text"] == "1 × 2"
    assert {r["status"] for r in rows} == {"PONTUADA"}


def test_extra_activities_stay_out_of_the_total(derived_case):
    case = derived_case
    before = score(case)
    container = case["client"].app.state.container
    # EDT-02: a manual activity cannot be dated outside the interstice any more, so the one
    # before it is created as an imported one (as the data of older processes came) and validated
    earlier = container.create_activity.execute(
        case["actor"],
        UUID(case["process"]["id"]),
        ActivityData(
            title="Orientação anterior ao interstício", group_number=2, item_number=7,
            quantity=Decimal(1), event_date=date(2022, 6, 1),
            period_precision=PeriodPrecision.MONTH, evidence_note="Declaração",
        ),
        source=ActivitySource.IMPORTADA,
    )  # fmt: skip
    with container.uow_factory() as uow:
        uow.activities.update(replace(earlier, status=ActivityStatus.VALIDADA), earlier.version)
        uow.commit()
    post(
        case, title="  ITEM 2.7 número 1 ", group_number=2, item_number=7, quantidade=1,
        event_date="2023-04-15", evidence_note="Declaração",
    )  # fmt: skip
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
    assert after["total"] == "211.00"
    assert after["group1_hours_by_period"] == EXPECTED_HOURS_BY_PERIOD
    assert after["group1_total_hours"] == "92.00"
    assert after["potential_total"] == "5.00"
    by_title = {r["title"]: r for r in after["rows"]}
    # SEG-01: outside the interstice and the duplicate are not valid, so they have no row
    assert "Orientação anterior ao interstício" not in by_title
    assert "ITEM 2.7 número 1" not in by_title
    waiting = by_title["Sugestão da IA"]
    assert (waiting["status"], waiting["points"], waiting["activity_status"]) == (
        "POTENCIAL", "5.00", "AGUARDANDO_REVISAO",
    )  # fmt: skip
    assert pending.status.value == "AGUARDANDO_REVISAO"
    assert after["counters"]["activities"] == before["counters"]["activities"] + 1
    assert after["counters"]["pending"] == 1
    assert after["counters"]["not_scored"] == before["counters"]["not_scored"]
    month_activity = next(
        a for a in case["client"].get(f"/api/processes/{case['process']['id']}/activities").json()
        if a["title"] == "Orientação anterior ao interstício"
    )  # fmt: skip
    assert month_activity["event_date"] == "2022-06"
    assert month_activity["period_precision"] == "MONTH"


def test_the_result_is_the_same_on_every_query(derived_case):
    assert score(derived_case) == score(derived_case)
