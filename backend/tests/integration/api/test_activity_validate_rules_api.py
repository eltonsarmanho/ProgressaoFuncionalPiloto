"""VAL-03, VAL-05, VAL-06: validating needs a category and a valid activity."""

import uuid
from datetime import date
from decimal import Decimal

import pytest

from app.application.use_cases.scoring import ActivityData
from app.domain.entities.activity import ActivitySource

D = Decimal


@pytest.fixture
def chosen(client, headers, process, scoring_tables):
    body = {"version_id": str(scoring_tables["OFICIAL"].id)}
    response = client.put(
        f"/api/processes/{process['id']}/scoring/table", json=body, headers=headers
    )
    assert response.status_code == 200, response.text
    return process


def draft(client, admin, process, **kw):
    """A suggested draft (AGUARDANDO_REVISAO); item III.4 and a date inside by default."""
    user, _ = admin
    fields = {
        "title": "Visão Computacional com OpenCV",
        "group_number": 3,
        "item_number": 4,
        "event_date": date(2023, 5, 10),
        "quantity": D(1),
        **kw,
    }
    return client.app.state.container.create_activity.execute(
        user, uuid.UUID(process["id"]), ActivityData(**fields), source=ActivitySource.SUGERIDA_IA
    )


def change(client, headers, activity, status, version=1):
    return client.post(
        f"/api/activities/{activity.id}/status",
        json={"status": status, "expected_version": version},
        headers=headers,
    )


def current(client, activity):
    return client.get(f"/api/activities/{activity.id}").json()


def test_validating_without_a_category_is_422_on_categoria_and_changes_nothing(
    client, admin, headers, chosen
):
    activity = draft(client, admin, chosen, group_number=None, item_number=None)

    response = change(client, headers, activity, "VALIDADA")

    assert response.status_code == 422, response.text
    assert response.json()["detail"] == [
        {"field": "categoria", "message": "Escolha a categoria antes de validar"}
    ]
    after = current(client, activity)
    assert (after["status"], after["version"]) == ("AGUARDANDO_REVISAO", 1)


def test_validating_an_activity_outside_the_interstice_is_422_with_its_code(
    client, admin, headers, chosen
):
    outside = draft(client, admin, chosen, event_date=date(2020, 1, 10))

    response = change(client, headers, outside, "VALIDADA")

    assert response.status_code == 422, response.text
    [error] = response.json()["detail"]
    assert error["field"] == "status"
    assert error["code"] == "ATIVIDADE_NAO_VALIDA"
    assert "interstício" in error["message"]
    assert current(client, outside)["status"] == "AGUARDANDO_REVISAO"


def test_validating_an_activity_below_the_minimum_hours_is_422_with_its_code(
    client, admin, headers, chosen
):
    short = draft(client, admin, chosen, title="Curso de extensão", group_number=4,
                  item_number=4, hours=D(19))  # fmt: skip

    response = change(client, headers, short, "VALIDADA")

    assert response.status_code == 422, response.text
    [error] = response.json()["detail"]
    assert (error["field"], error["code"]) == ("status", "ATIVIDADE_NAO_VALIDA")
    assert "19" in error["message"] and "20" in error["message"]
    assert current(client, short)["status"] == "AGUARDANDO_REVISAO"


def test_validating_a_categorized_activity_inside_the_interstice_is_200_and_audited_without_justification(  # noqa: E501
    client, admin, headers, chosen, uow_factory
):
    activity = draft(client, admin, chosen)

    response = change(client, headers, activity, "VALIDADA")

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "VALIDADA"
    with uow_factory() as uow:
        events = [
            e
            for e in uow.audit.list_for("activity", str(activity.id))
            if e.action.value == "STATUS"
        ]
    assert len(events) == 1
    assert events[0].justification is None


def test_rejecting_and_reopening_an_activity_without_a_category_work(
    client, admin, headers, chosen
):
    activity = draft(client, admin, chosen, group_number=None, item_number=None)

    rejected = change(client, headers, activity, "REJEITADA")
    reopened = change(client, headers, activity, "AGUARDANDO_REVISAO", version=2)

    assert rejected.status_code == 200, rejected.text
    assert rejected.json()["status"] == "REJEITADA"
    assert reopened.status_code == 200, reopened.text
    assert reopened.json()["status"] == "AGUARDANDO_REVISAO"


def test_rejecting_an_activity_outside_the_interstice_works(client, admin, headers, chosen):
    outside = draft(client, admin, chosen, event_date=date(2020, 1, 10))

    response = change(client, headers, outside, "REJEITADA")

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "REJEITADA"
