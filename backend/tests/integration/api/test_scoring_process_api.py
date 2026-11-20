"""SEL-02..SEL-08, CALC-12: process scoring routes (table choice and calculated result)."""

import uuid
from datetime import date
from decimal import Decimal

import pytest

from app.domain.entities.activity import Activity, ActivityStatus
from app.domain.entities.user import Role
from tests.integration.api.factories import add_professor, mark_pending, process_payload
from tests.support.process_status import conclude_for_test

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


def test_potential_points_are_split_into_dated_and_undated_in_the_response(
    client, admin, process, scoring_tables, uow_factory
):
    _, headers = admin
    mark_pending(uow_factory, scoring_tables["OFICIAL"])
    choose(client, headers, process, scoring_tables["OFICIAL"])
    pending = ActivityStatus.AGUARDANDO_REVISAO
    add_activity(
        uow_factory, process, title="Com data", group_number=2, item_number=7,
        quantity=D("2"), status=pending,
    )  # fmt: skip
    add_activity(
        uow_factory, process, title="Sem data", group_number=2, item_number=7,
        quantity=D("1"), status=pending, event_date=None,
    )  # fmt: skip

    body = client.get(f"/api/processes/{process['id']}/scoring").json()

    assert body["potential_total"] == "15.00"  # item 2.7 is worth 5 points
    assert body["potential_dated"] == "10.00"
    assert body["potential_undated"] == "5.00"


def test_table_route_suggests_the_unit_table_without_choosing(client, process):
    response = client.get(table_url(process))

    assert response.status_code == 200
    body = response.json()
    assert body["chosen"] is None
    assert body["suggested"]["table_name"] == "Tabela de Pontuação da UFPA"
    assert body["suggested"]["version"]["status"] == "OFICIAL"
    assert body["alerts"] == []
    assert client.get(table_url(process)).json()["chosen"] is None


def test_unit_without_valid_table_gets_not_found_alert(client, admin, reference, uow_factory):
    _, headers = admin
    professor = add_professor(uow_factory, reference["FASI"], siape="7654321")
    old = {**process_payload(professor), "start_date": "2010-01-01", "end_date": "2012-01-01"}
    created = client.post("/api/processes", json=old, headers=headers).json()

    body = client.get(table_url(created)).json()

    assert body["suggested"] is None
    assert alert_map(body) == {"TABELA_NAO_ENCONTRADA": "REQUER_ANALISE_NORMATIVA"}


def test_choosing_saves_and_reports_pending_validation_alert(
    client, admin, process, scoring_tables, uow_factory
):
    _, headers = admin
    mark_pending(uow_factory, scoring_tables["OFICIAL"])

    response = choose(client, headers, process, scoring_tables["OFICIAL"])

    assert response.status_code == 200
    body = response.json()
    assert body["chosen"]["version"]["id"] == str(scoring_tables["OFICIAL"].id)
    assert alert_map(body) == {"TABELA_PENDENTE_VALIDACAO": "REQUER_ANALISE_NORMATIVA"}
    assert client.get(table_url(process)).json()["chosen"] == body["chosen"]


def test_other_unit_table_needs_no_justification_and_alerts(client, admin, process, scoring_tables):
    _, headers = admin

    accepted = choose(client, headers, process, scoring_tables["OUTRA"])  # UIM-18

    assert accepted.status_code == 200
    assert alert_map(accepted.json()) == {"TABELA_DE_OUTRA_UNIDADE": "ALERTA"}


def test_version_not_valid_on_interstice_end_alerts(
    client, admin, reference, uow_factory, scoring_tables
):
    _, headers = admin
    professor = add_professor(uow_factory, reference["FASI"], siape="7654321")
    old = {**process_payload(professor), "start_date": "2010-01-01", "end_date": "2012-01-01"}
    created = client.post("/api/processes", json=old, headers=headers).json()

    body = choose(client, headers, created, scoring_tables["OFICIAL"]).json()

    assert alert_map(body)["TABELA_FORA_DE_VIGENCIA"] == "ALERTA"


def test_unknown_version_is_422_on_version_id(client, admin, process, scoring_tables):
    _, headers = admin
    body = {"version_id": str(uuid.uuid4())}

    response = client.put(table_url(process), json=body, headers=headers)

    assert response.status_code == 422
    assert response.json()["detail"][0]["field"] == "version_id"


def test_choosing_a_superseded_version_is_422_with_the_code_versao_substituida(
    client, admin, process, scoring_tables, uow_factory
):
    """GI-07: `PUT /scoring/table` refuses a version another one replaced."""
    _, headers = admin
    official = scoring_tables["OFICIAL"]
    with uow_factory() as uow:
        uow.scoring_tables.set_superseded(official.id, scoring_tables["OUTRA"].id)
        uow.commit()

    response = choose(client, headers, process, official)

    assert response.status_code == 422, response.text
    [error] = response.json()["detail"]
    assert (error["field"], error["code"]) == ("version_id", "VERSAO_SUBSTITUIDA")
    assert client.get(table_url(process)).json()["chosen"] is None


def test_choice_is_audited_in_the_process_history(client, admin, process, scoring_tables):
    _, headers = admin
    choose(client, headers, process, scoring_tables["OFICIAL"], justificativa="Confirmada")

    history = client.get(f"/api/processes/{process['id']}/history").json()

    event = history[-1]
    assert event["changes"] == {
        "scoring_table_version_id": {"before": None, "after": str(scoring_tables["OFICIAL"].id)}
    }
    assert event["justification"] == "Confirmada"


def test_chosen_version_becomes_in_use(client, admin, process, scoring_tables):
    _, headers = admin
    url = f"/api/scoring-versions/{scoring_tables["OFICIAL"].id}"
    assert client.get(url).json()["in_use"] is False

    choose(client, headers, process, scoring_tables["OFICIAL"])

    assert client.get(url).json()["in_use"] is True


def test_stale_process_version_and_closed_process_are_409(
    client, admin, process, scoring_tables, uow_factory
):
    _, headers = admin

    stale = choose(client, headers, process, scoring_tables["OFICIAL"], expected_version=99)
    current = client.get(f"/api/processes/{process['id']}").json()["version"]
    client.post(
        f"/api/processes/{process['id']}/status",
        json={"status": "EM_ANDAMENTO", "expected_version": current, "justificativa": "x"},
        headers=headers,
    )
    conclude_for_test(uow_factory, process["id"])
    closed = choose(client, headers, process, scoring_tables["OFICIAL"])

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
    assert body["suggested"]["table_name"] == "Tabela de Pontuação da UFPA"
    assert [(r["status"], r["reasons"]) for r in body["rows"]] == [
        ("NAO_PONTUADA", ["SEM_TABELA"])
    ]
    assert body["minimum"]["status"] == "NAO_DEFINIDO"


def test_scoring_result_has_rows_reasons_alerts_and_decimal_text(
    client, admin, process, scoring_tables, uow_factory
):
    _, headers = admin
    mark_pending(uow_factory, scoring_tables["OFICIAL"])
    choose(client, headers, process, scoring_tables["OFICIAL"])
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
        (2, "20.00"),
        (3, "0.00"),
    ]
    assert body["total"] == "20.00"
    assert body["potential_total"] == "0.00"
    assert (body["potential_dated"], body["potential_undated"]) == ("0.00", "0.00")
    assert body["group1_percent"] == "0.00"
    # SEG-01: the activity outside the interstice is not valid, has no row and is not counted
    assert body["counters"] == {
        "activities": 1, "with_evidence": 0, "pending": 0, "not_scored": 0, "with_alerts": 1,
    }  # fmt: skip
    [scored] = body["rows"]
    assert (scored["title"], scored["group_number"], scored["item_number"]) == ("Orientação", 2, 7)
    assert (scored["unit_points"], scored["effective_quantity"]) == ("5.00", "4.00")
    assert (scored["formula_text"], scored["points"], scored["status"]) == (
        "4 × 5", "20.00", "PONTUADA",
    )  # fmt: skip
    assert [(a["code"], a["severity"]) for a in scored["alerts"]] == [("SEM_COMPROVANTE", "ALERTA")]
    assert scored["alerts"][0]["norm_reference"]
    assert body["alerts"] and alert_map(body)["TABELA_PENDENTE_VALIDACAO"] == (
        "REQUER_ANALISE_NORMATIVA"
    )
    assert body["minimum"] == {"status": "NAO_ATINGE", "minimum": "100.00", "total": "20.00"}


@pytest.mark.parametrize("path", ["scoring", "scoring/table"])
def test_routes_of_a_process_outside_access_are_404(client, act_as, reference, process, path):
    act_as("sec.ifch@ufpa.br", Role.SECRETARIA, unit_ids=frozenset({reference["IFCH"].id}))

    assert client.get(f"/api/processes/{process['id']}/{path}").status_code == 404
    assert client.get(f"/api/processes/{uuid.uuid4()}/{path}").status_code == 404


def test_put_of_a_process_outside_access_is_404(client, act_as, reference, process, scoring_tables):
    _, headers = act_as(
        "sec.ifch@ufpa.br", Role.SECRETARIA, unit_ids=frozenset({reference["IFCH"].id})
    )

    assert choose(client, headers, process, scoring_tables["OFICIAL"]).status_code == 404


def test_put_requires_the_csrf_token(client, admin, process, scoring_tables):
    body = {"version_id": str(scoring_tables["OFICIAL"].id)}

    assert client.put(table_url(process), json=body).status_code == 403


def test_routes_require_a_session(client, process):
    for suffix in ("scoring", "scoring/table"):
        client.cookies.clear()
        assert client.get(f"/api/processes/{process['id']}/{suffix}").status_code == 401
