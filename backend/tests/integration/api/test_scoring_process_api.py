"""SEL-02..SEL-08, CALC-12: process scoring routes (table choice and calculated result)."""

import uuid
from datetime import date
from decimal import Decimal

import pytest

from app.domain.entities.activity import Activity
from app.domain.entities.user import Role
from tests.integration.api.factories import add_professor, process_payload

D = Decimal


@pytest.fixture
def admin(act_as, scoring_tables):
    return act_as("admin@ufpa.br", Role.ADMIN)


@pytest.fixture
def process(client, admin, reference, uow_factory):
    _, headers = admin
    professor = add_professor(uow_factory, reference["FASI"])
    response = client.post("/api/processes", json=process_payload(professor), headers=headers)
    assert response.status_code == 201
    return response.json()


def table_url(process):
    return f"/api/processes/{process['id']}/scoring/table"


def choose(client, headers, process, version, **body):
    body = {"version_id": str(version.id), **body}
    return client.put(table_url(process), json=body, headers=headers)


def alert_map(body):
    return {a["code"]: a["severity"] for a in body["alerts"]}


def add_activity(uow_factory, process, **kw):
    kw.setdefault("event_date", date(2023, 5, 10))
    with uow_factory() as uow:
        creator = uow.users.get_by_email("admin@ufpa.br")
        activity = Activity(
            id=uuid.uuid4(), process_id=uuid.UUID(process["id"]), created_by=creator.id, **kw
        )
        uow.activities.add(activity)
        uow.commit()
    return activity


def test_table_route_suggests_the_unit_table_without_choosing(client, process):
    response = client.get(table_url(process))

    assert response.status_code == 200
    body = response.json()
    assert body["chosen"] is None
    assert body["suggested"]["table_name"] == "Tabela de Pontuação da FASI"
    assert body["suggested"]["version"]["status"] == "PENDENTE_VALIDACAO"
    assert body["alerts"] == []
    assert client.get(table_url(process)).json()["chosen"] is None


def test_unit_without_valid_table_gets_not_found_alert(client, admin, reference, uow_factory):
    _, headers = admin
    professor = add_professor(uow_factory, reference["FASI"], siape="7654321")
    old = {**process_payload(professor), "start_date": "2018-01-01", "end_date": "2020-01-01"}
    created = client.post("/api/processes", json=old, headers=headers).json()

    body = client.get(table_url(created)).json()

    assert body["suggested"] is None
    assert alert_map(body) == {"TABELA_NAO_ENCONTRADA": "REQUER_ANALISE_NORMATIVA"}


def test_choosing_saves_and_reports_pending_validation_alert(
    client, admin, process, scoring_tables
):
    _, headers = admin

    response = choose(client, headers, process, scoring_tables["FASI"])

    assert response.status_code == 200
    body = response.json()
    assert body["chosen"]["version"]["id"] == str(scoring_tables["FASI"].id)
    assert alert_map(body) == {"TABELA_PENDENTE_VALIDACAO": "REQUER_ANALISE_NORMATIVA"}
    assert client.get(table_url(process)).json()["chosen"] == body["chosen"]


def test_other_unit_table_needs_justification_then_alerts(client, admin, process, scoring_tables):
    _, headers = admin

    refused = choose(client, headers, process, scoring_tables["IFCH"])
    accepted = choose(client, headers, process, scoring_tables["IFCH"], justificativa="Sem tabela")

    assert refused.status_code == 422
    assert refused.json()["detail"][0]["field"] == "justificativa"
    assert accepted.status_code == 200
    assert alert_map(accepted.json()) == {"TABELA_DE_OUTRA_UNIDADE": "ALERTA"}


def test_version_not_valid_on_interstice_end_alerts(
    client, admin, reference, uow_factory, scoring_tables
):
    _, headers = admin
    professor = add_professor(uow_factory, reference["FASI"], siape="7654321")
    old = {**process_payload(professor), "start_date": "2018-01-01", "end_date": "2020-01-01"}
    created = client.post("/api/processes", json=old, headers=headers).json()

    body = choose(client, headers, created, scoring_tables["FASI"]).json()

    assert alert_map(body)["TABELA_FORA_DE_VIGENCIA"] == "ALERTA"


def test_unknown_version_is_422_on_version_id(client, admin, process, scoring_tables):
    _, headers = admin
    body = {"version_id": str(uuid.uuid4())}

    response = client.put(table_url(process), json=body, headers=headers)

    assert response.status_code == 422
    assert response.json()["detail"][0]["field"] == "version_id"


def test_choice_is_audited_in_the_process_history(client, admin, process, scoring_tables):
    _, headers = admin
    choose(client, headers, process, scoring_tables["FASI"], justificativa="Confirmada")

    history = client.get(f"/api/processes/{process['id']}/history").json()

    event = history[-1]
    assert event["changes"] == {
        "scoring_table_version_id": {"before": None, "after": str(scoring_tables["FASI"].id)}
    }
    assert event["justification"] == "Confirmada"


def test_chosen_version_becomes_in_use(client, admin, process, scoring_tables):
    _, headers = admin
    url = f"/api/scoring-versions/{scoring_tables['FASI'].id}"
    assert client.get(url).json()["in_use"] is False

    choose(client, headers, process, scoring_tables["FASI"])

    assert client.get(url).json()["in_use"] is True


def test_stale_process_version_and_closed_process_are_409(client, admin, process, scoring_tables):
    _, headers = admin

    stale = choose(client, headers, process, scoring_tables["FASI"], expected_version=99)
    for status in ("EM_ANDAMENTO", "CONCLUIDO"):
        current = client.get(f"/api/processes/{process['id']}").json()["version"]
        client.post(
            f"/api/processes/{process['id']}/status",
            json={"status": status, "expected_version": current, "justificativa": "x"},
            headers=headers,
        )
    closed = choose(client, headers, process, scoring_tables["FASI"])

    assert stale.status_code == 409
    assert closed.status_code == 409


def test_scoring_without_table_has_zero_total_sem_tabela_and_suggestion(
    client, process, uow_factory
):
    add_activity(uow_factory, process, title="Orientação", group_number=2, item_number=7)

    response = client.get(f"/api/processes/{process['id']}/scoring")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == "0.00"
    assert body["chosen"] is None
    assert body["suggested"]["table_name"] == "Tabela de Pontuação da FASI"
    assert [(r["status"], r["reasons"]) for r in body["rows"]] == [
        ("NAO_PONTUADA", ["SEM_TABELA"])
    ]
    assert body["minimum"]["status"] == "NAO_DEFINIDO"


def test_scoring_result_has_rows_reasons_alerts_and_decimal_text(
    client, admin, process, scoring_tables, uow_factory
):
    _, headers = admin
    choose(client, headers, process, scoring_tables["FASI"])
    add_activity(
        uow_factory, process, title="Orientação", group_number=2, item_number=7, quantity=D("4")
    )
    add_activity(
        uow_factory, process, title="Fora", group_number=2, item_number=8,
        event_date=date(2020, 1, 1), evidence_note="ok",
    )  # fmt: skip

    body = client.get(f"/api/processes/{process['id']}/scoring").json()

    assert [(s["group_number"], s["subtotal"]) for s in body["subtotals"]][:3] == [
        (1, "0.00"),
        (2, "40.00"),
        (3, "0.00"),
    ]
    assert body["total"] == "40.00"
    assert body["potential_total"] == "0.00"
    assert body["group1_percent"] == "0.00"
    assert body["counters"] == {
        "activities": 2, "with_evidence": 1, "pending": 0, "not_scored": 1, "with_alerts": 1,
    }  # fmt: skip
    scored, outside = body["rows"]
    assert (scored["title"], scored["group_number"], scored["item_number"]) == ("Orientação", 2, 7)
    assert (scored["unit_points"], scored["effective_quantity"]) == ("10.00", "4.00")
    assert (scored["formula_text"], scored["points"], scored["status"]) == (
        "4 × 10", "40.00", "PONTUADA",
    )  # fmt: skip
    assert [(a["code"], a["severity"]) for a in scored["alerts"]] == [("SEM_COMPROVANTE", "ALERTA")]
    assert scored["alerts"][0]["norm_reference"]
    assert (outside["status"], outside["reasons"], outside["points"]) == (
        "NAO_PONTUADA",
        ["FORA_DO_INTERSTICIO"],
        "0.00",
    )
    assert body["alerts"] and alert_map(body)["TABELA_PENDENTE_VALIDACAO"] == (
        "REQUER_ANALISE_NORMATIVA"
    )
    assert body["minimum"] == {"status": "NAO_ATINGE", "minimum": "100.00", "total": "40.00"}


@pytest.mark.parametrize("path", ["scoring", "scoring/table"])
def test_routes_of_a_process_outside_access_are_404(client, act_as, reference, process, path):
    act_as("sec.ifch@ufpa.br", Role.SECRETARIA, unit_ids=frozenset({reference["IFCH"].id}))

    assert client.get(f"/api/processes/{process['id']}/{path}").status_code == 404
    assert client.get(f"/api/processes/{uuid.uuid4()}/{path}").status_code == 404


def test_put_of_a_process_outside_access_is_404(client, act_as, reference, process, scoring_tables):
    _, headers = act_as(
        "sec.ifch@ufpa.br", Role.SECRETARIA, unit_ids=frozenset({reference["IFCH"].id})
    )

    assert choose(client, headers, process, scoring_tables["FASI"]).status_code == 404


def test_put_requires_the_csrf_token(client, admin, process, scoring_tables):
    body = {"version_id": str(scoring_tables["FASI"].id)}

    assert client.put(table_url(process), json=body).status_code == 403


def test_routes_require_a_session(client, process):
    for suffix in ("scoring", "scoring/table"):
        client.cookies.clear()
        assert client.get(f"/api/processes/{process['id']}/{suffix}").status_code == 401
