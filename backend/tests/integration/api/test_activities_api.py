"""ATV-01, ATV-05..ATV-09, ATV-11..ATV-14: activity routes."""

import uuid

import pytest

from app.domain.entities.user import Role
from tests.integration.api.factories import add_professor, process_payload


@pytest.fixture
def admin(act_as, scoring_tables):
    return act_as("admin@ufpa.br", Role.ADMIN)


@pytest.fixture
def headers(admin):
    return admin[1]


@pytest.fixture
def process(client, admin, reference, uow_factory):
    professor = add_professor(uow_factory, reference["FASI"])
    response = client.post("/api/processes", json=process_payload(professor), headers=admin[1])
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def chosen(client, headers, process, scoring_tables):
    body = {"version_id": str(scoring_tables["OFICIAL"].id)}
    response = client.put(
        f"/api/processes/{process['id']}/scoring/table", json=body, headers=headers
    )
    assert response.status_code == 200
    return process


@pytest.fixture
def points_chosen(client, headers, process, points_table):
    """A table whose group I counts in points (the official one refuses informed points there)."""
    body = {"version_id": str(points_table.id), "justificativa": "Teste"}
    response = client.put(
        f"/api/processes/{process['id']}/scoring/table", json=body, headers=headers
    )
    assert response.status_code == 200
    return process


def activities_url(process):
    return f"/api/processes/{process['id']}/activities"


def body(**kw):
    return {"title": "Orientação de TCC", "event_date": "2023-05-10", **kw}


def create(client, headers, process, **kw):
    response = client.post(activities_url(process), json=body(**kw), headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def field_error(response, field):
    assert response.status_code == 422, response.text
    assert response.json()["detail"][0]["field"] == field


def test_create_returns_201_with_manual_validated_activity(client, headers, chosen):
    response = client.post(
        activities_url(chosen),
        json=body(group_number=2, item_number=7, quantidade=4, evidence_note="Declaração"),
        headers=headers,
    )

    assert response.status_code == 201
    created = response.json()
    assert created["status"] == "VALIDADA"
    assert created["source"] == "MANUAL"
    assert created["version"] == 1
    assert (created["group_number"], created["item_number"]) == (2, 7)
    assert created["quantidade"] == "4.00"
    assert created["event_date"] == "2023-05-10"
    assert created["period_precision"] == "DAY"
    assert created["evidence_note"] == "Declaração"
    assert client.get(f"/api/activities/{created['id']}").json() == created


@pytest.mark.parametrize("extra", [{"source": "SUGERIDA_IA"}, {"source": "MANUAL"}])
def test_public_api_does_not_accept_source(client, headers, chosen, extra):
    response = client.post(activities_url(chosen), json=body(**extra), headers=headers)

    field_error(response, "source")
    assert client.get(activities_url(chosen)).json() == []


def test_public_api_does_not_accept_status_on_create(client, headers, chosen):
    field_error(
        client.post(activities_url(chosen), json=body(status="REJEITADA"), headers=headers),
        "status",
    )


def test_month_only_dates_are_stored_with_month_precision(client, headers, chosen):
    created = create(
        client, headers, chosen, event_date=None, period_start="2022-12", period_end="2022-12"
    )

    assert created["period_precision"] == "MONTH"
    assert (created["period_start"], created["period_end"]) == ("2022-12", "2022-12")
    single = create(client, headers, chosen, event_date="2023-06")
    assert (single["event_date"], single["period_precision"]) == ("2023-06", "MONTH")


@pytest.mark.parametrize("bad", ["2022-13", "31/05/2022", "2022-5", "abc"])
def test_invalid_date_is_422_on_that_field(client, headers, chosen, bad):
    field_error(
        client.post(activities_url(chosen), json=body(period_start=bad), headers=headers),
        "period_start",
    )


def test_group_one_derives_item_from_level_and_requires_its_inputs(client, headers, chosen):
    base = {"group_number": 1, "academic_period": "2023.1", "level": "POS_GRADUACAO", "horas": 68}

    created = create(client, headers, chosen, **base)
    missing = client.post(
        activities_url(chosen), json=body(**{**base, "academic_period": None}), headers=headers
    )

    assert (created["item_number"], created["horas"]) == (2, "68.00")
    field_error(missing, "academic_period")


@pytest.mark.parametrize(
    ("changes", "field"),
    [
        ({"quantidade": -1}, "quantidade"),
        ({"quantidade": 10001}, "quantidade"),
        ({"group_number": 2, "item_number": 7, "quantidade": 1.5}, "quantidade"),
        ({"quantidade": "abc"}, "quantidade"),
        ({"horas": -1}, "horas"),
        ({"horas": 10001}, "horas"),
        ({"title": "t" * 301}, "title"),
        ({"evidence_note": "n" * 501}, "evidence_note"),
        ({"points_override": 5, "group_number": 2, "item_number": 7}, "points_override"),
        ({"level": "OUTRO"}, "level"),
    ],
)
def test_invalid_inputs_are_422_with_the_field_name(client, headers, chosen, changes, field):
    field_error(client.post(activities_url(chosen), json=body(**changes), headers=headers), field)


def test_points_override_without_justification_is_422_on_justificativa(
    client, headers, points_chosen
):
    payload = body(
        points_override=5, group_number=1, academic_period="2023.1", level="GRADUACAO", horas=68
    )

    field_error(
        client.post(activities_url(points_chosen), json=payload, headers=headers), "justificativa"
    )


def test_points_override_with_justification_is_saved_for_weekly_load(
    client, headers, points_chosen
):
    created = create(
        client, headers, points_chosen, group_number=1, academic_period="2023.1", level="GRADUACAO",
        horas=68, points_override=24, justificativa="Declaração da unidade",
    )  # fmt: skip

    assert created["points_override"] == "24.00"


def test_activity_without_classification_is_saved(client, headers, chosen):
    created = create(client, headers, chosen)

    assert (created["group_number"], created["item_number"]) == (None, None)
    scoring = client.get(f"/api/processes/{chosen['id']}/scoring").json()
    assert scoring["rows"][0]["reasons"] == ["SEM_ENQUADRAMENTO"]


def test_list_orders_by_group_item_date_and_filters(client, headers, chosen):
    create(client, headers, chosen, title="b", group_number=3, item_number=2)
    rejected = create(client, headers, chosen, title="a2", group_number=2, item_number=7)
    create(
        client, headers, chosen, title="a1", group_number=2, item_number=7, event_date="2023-01-01"
    )
    client.post(
        f"/api/activities/{rejected['id']}/status",
        json={"status": "REJEITADA", "expected_version": 1, "justificativa": "Erro"},
        headers=headers,
    )

    everything = client.get(activities_url(chosen)).json()
    group_two = client.get(activities_url(chosen), params={"group": 2}).json()
    rejected_only = client.get(activities_url(chosen), params={"status": "REJEITADA"}).json()
    combined = client.get(activities_url(chosen), params={"group": 3, "status": "REJEITADA"}).json()

    assert [a["title"] for a in everything] == ["a1", "a2", "b"]
    assert [a["title"] for a in group_two] == ["a1", "a2"]
    assert [a["title"] for a in rejected_only] == ["a2"]
    assert combined == []


def test_invalid_status_filter_is_422_on_status(client, headers, chosen):
    field_error(client.get(activities_url(chosen), params={"status": "X"}), "status")


def test_put_with_justification_updates_and_bumps_version(client, headers, chosen):
    created = create(client, headers, chosen, group_number=2, item_number=7, quantidade=4)

    response = client.put(
        f"/api/activities/{created['id']}",
        json=body(
            group_number=2,
            item_number=7,
            quantidade=5,
            expected_version=1,
            justificativa="Mais uma",
        ),
        headers=headers,
    )

    assert response.status_code == 200
    assert (response.json()["quantidade"], response.json()["version"]) == ("5.00", 2)


def test_put_changing_scoring_inputs_without_justification_is_422(client, headers, chosen):
    created = create(client, headers, chosen, group_number=2, item_number=7, quantidade=4)
    url = f"/api/activities/{created['id']}"
    payload = body(group_number=2, item_number=7, quantidade=5, expected_version=1)

    field_error(client.put(url, json=payload, headers=headers), "justificativa")
    assert client.get(url).json()["quantidade"] == "4.00"


def test_put_requires_expected_version_and_detects_stale_writes(client, headers, chosen):
    created = create(client, headers, chosen)
    url = f"/api/activities/{created['id']}"
    ok = client.put(url, json=body(title="Novo título", expected_version=1), headers=headers)

    missing = client.put(url, json=body(), headers=headers)
    stale = client.put(url, json=body(title="Outro", expected_version=1), headers=headers)

    assert ok.status_code == 200
    field_error(missing, "expected_version")
    assert stale.status_code == 409
    assert client.get(url).json()["title"] == "Novo título"


def test_status_change_needs_justification_and_valid_status(client, headers, chosen):
    created = create(client, headers, chosen)
    url = f"/api/activities/{created['id']}/status"

    no_reason = client.post(
        url, json={"status": "REJEITADA", "expected_version": 1}, headers=headers
    )
    bad_value = client.post(
        url,
        json={"status": "PENDENTE", "expected_version": 1, "justificativa": "x"},
        headers=headers,
    )
    ok = client.post(
        url,
        json={"status": "REJEITADA", "expected_version": 1, "justificativa": "Erro"},
        headers=headers,
    )

    field_error(no_reason, "justificativa")
    field_error(bad_value, "status")
    assert ok.status_code == 200
    assert (ok.json()["status"], ok.json()["version"]) == ("REJEITADA", 2)
    stale = client.post(
        url,
        json={"status": "VALIDADA", "expected_version": 1, "justificativa": "x"},
        headers=headers,
    )
    assert stale.status_code == 409


def test_distinct_mark_releases_a_duplicate_in_the_result(client, headers, chosen):
    create(client, headers, chosen, group_number=2, item_number=7, quantidade=1)
    twin = create(
        client,
        headers,
        chosen,
        title=" ORIENTAÇÃO de tcc",
        group_number=2,
        item_number=7,
        quantidade=1,
    )
    scoring_url = f"/api/processes/{chosen['id']}/scoring"
    assert [r["reasons"] for r in client.get(scoring_url).json()["rows"]] == [[], ["DUPLICIDADE"]]

    url = f"/api/activities/{twin['id']}/distinct"
    blank = client.post(url, json={"expected_version": 1, "justificativa": " "}, headers=headers)
    ok = client.post(
        url, json={"expected_version": 1, "justificativa": "Outro aluno"}, headers=headers
    )

    field_error(blank, "justificativa")
    assert ok.status_code == 200
    assert ok.json()["distinct_justification"] == "Outro aluno"
    assert client.get(scoring_url).json()["total"] == "10.00"


@pytest.mark.parametrize("final", ["CONCLUIDO", "ARQUIVADO"])
def test_writes_on_a_closed_process_are_409(client, headers, chosen, final):
    created = create(client, headers, chosen)
    current = chosen
    for status in ("EM_ANDAMENTO", "CONCLUIDO") if final == "CONCLUIDO" else ("ARQUIVADO",):
        version = client.get(f"/api/processes/{current['id']}").json()["version"]
        response = client.post(
            f"/api/processes/{current['id']}/status",
            json={"status": status, "expected_version": version, "justificativa": "x"},
            headers=headers,
        )
        assert response.status_code == 200, response.text
    url = f"/api/activities/{created['id']}"

    assert client.post(activities_url(chosen), json=body(), headers=headers).status_code == 409
    assert client.put(url, json=body(expected_version=1), headers=headers).status_code == 409
    status_body = {"status": "REJEITADA", "expected_version": 1, "justificativa": "x"}
    assert client.post(f"{url}/status", json=status_body, headers=headers).status_code == 409
    distinct_body = {"expected_version": 1, "justificativa": "x"}
    assert client.post(f"{url}/distinct", json=distinct_body, headers=headers).status_code == 409
    assert client.get(url).status_code == 200


def test_everything_outside_access_is_404(client, act_as, reference, headers, chosen):
    created = create(client, headers, chosen)
    _, other = act_as(
        "sec.ifch@ufpa.br", Role.SECRETARIA, unit_ids=frozenset({reference["IFCH"].id})
    )
    url = f"/api/activities/{created['id']}"
    unknown = f"/api/activities/{uuid.uuid4()}"

    assert client.get(activities_url(chosen)).status_code == 404
    assert client.post(activities_url(chosen), json=body(), headers=other).status_code == 404
    assert client.get(url).status_code == 404
    assert client.put(url, json=body(expected_version=1), headers=other).status_code == 404
    status_body = {"status": "REJEITADA", "expected_version": 1, "justificativa": "x"}
    assert client.post(f"{url}/status", json=status_body, headers=other).status_code == 404
    assert (
        client.post(
            f"{url}/distinct", json={"expected_version": 1, "justificativa": "x"}, headers=other
        ).status_code
        == 404
    )
    assert client.get(unknown).status_code == 404
    assert client.put(unknown, json=body(expected_version=1), headers=other).status_code == 404
    assert client.get(f"/api/processes/{uuid.uuid4()}/activities").status_code == 404


def test_docente_owner_and_unit_secretaria_have_access(
    client, act_as, reference, process, headers, chosen, uow_factory
):
    created = create(client, headers, chosen)
    with uow_factory() as uow:
        professor_id = uow.processes.get(uuid.UUID(process["id"])).professor_id
    act_as("docente@ufpa.br", Role.DOCENTE, professor_id=professor_id)
    assert client.get(f"/api/activities/{created['id']}").status_code == 200
    act_as("sec.fasi@ufpa.br", Role.SECRETARIA, unit_ids=frozenset({reference["FASI"].id}))
    assert client.get(activities_url(chosen)).status_code == 200


def test_writes_require_csrf_and_every_route_a_session(client, headers, chosen):
    created = create(client, headers, chosen)
    url = f"/api/activities/{created['id']}"

    assert client.post(activities_url(chosen), json=body()).status_code == 403
    assert client.put(url, json=body(expected_version=1)).status_code == 403
    assert client.post(f"{url}/status", json={}).status_code == 403
    assert client.post(f"{url}/distinct", json={}).status_code == 403
    client.cookies.clear()
    for method, target in (
        ("GET", activities_url(chosen)),
        ("POST", activities_url(chosen)),
        ("GET", url),
        ("PUT", url),
        ("POST", f"{url}/status"),
        ("POST", f"{url}/distinct"),
    ):
        assert client.request(method, target).status_code == 401
