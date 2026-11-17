"""REV-02, REV-03, REV-04 (T40): the bulk validation route."""

import uuid
from datetime import date
from decimal import Decimal

import pytest

from app.application.use_cases.scoring import ActivityData
from app.domain.entities.activity import ActivitySource
from app.domain.entities.user import Role
from tests.integration.api.factories import process_payload
from tests.integration.api.test_documents_api import close_process


@pytest.fixture
def chosen(client, headers, process, scoring_tables):
    body = {"version_id": str(scoring_tables["OFICIAL"].id)}
    response = client.put(
        f"/api/processes/{process['id']}/scoring/table", json=body, headers=headers
    )
    assert response.status_code == 200, response.text
    return process


def draft(client, admin, process, title):
    """A suggested draft (AGUARDANDO_REVISAO) of item III.4, as the extraction creates it."""
    user, _ = admin
    return client.app.state.container.create_activity.execute(
        user,
        uuid.UUID(process["id"]),
        ActivityData(
            title=title,
            group_number=3,
            item_number=4,
            event_date=date(2023, 5, 10),
            quantity=Decimal(1),
        ),
        source=ActivitySource.SUGERIDA_IA,
    )


def url(process):
    return f"/api/processes/{process['id']}/activities/validate-batch"


def status_of(client, activity):
    return client.get(f"/api/activities/{activity.id}").json()["status"]


def score(client, process):
    return client.get(f"/api/processes/{process['id']}/scoring").json()


def test_it_validates_the_listed_activities_and_returns_each_one(
    client, admin, headers, chosen
):
    first, second, untouched = (draft(client, admin, chosen, t) for t in ("A", "B", "C"))

    response = client.post(
        url(chosen),
        json={"activity_ids": [str(first.id), str(second.id)], "justificativa": "Conferi"},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert [a["id"] for a in body] == [str(first.id), str(second.id)]
    assert [a["status"] for a in body] == ["VALIDADA", "VALIDADA"]
    assert [a["version"] for a in body] == [2, 2]
    assert [a["title"] for a in body] == ["A", "B"]
    assert all("evidences" in a for a in body)
    assert status_of(client, untouched) == "AGUARDANDO_REVISAO"


def test_validating_changes_the_scoring_total(client, admin, headers, chosen):
    first, second = draft(client, admin, chosen, "A"), draft(client, admin, chosen, "B")
    before = score(client, chosen)

    client.post(
        url(chosen),
        json={"activity_ids": [str(first.id), str(second.id)], "justificativa": "Conferi"},
        headers=headers,
    )

    after = score(client, chosen)
    assert before["total"] == "0.00"
    assert Decimal(before["potential_total"]) > 0  # the pending drafts only count as potential
    assert after["total"] == before["potential_total"]
    assert after["potential_total"] == "0.00"


def test_an_activity_of_another_process_is_404_and_none_is_validated(
    client, admin, headers, chosen, professor
):
    other = client.post("/api/processes", json=process_payload(professor), headers=headers).json()
    mine = draft(client, admin, chosen, "Minha")
    foreign = draft(client, admin, other, "De outro processo")

    response = client.post(
        url(chosen),
        json={"activity_ids": [str(mine.id), str(foreign.id)], "justificativa": "Conferi"},
        headers=headers,
    )

    assert response.status_code == 404
    assert status_of(client, mine) == "AGUARDANDO_REVISAO"
    assert status_of(client, foreign) == "AGUARDANDO_REVISAO"


def test_an_unknown_activity_is_404_and_none_is_validated(client, admin, headers, chosen):
    mine = draft(client, admin, chosen, "Minha")

    response = client.post(
        url(chosen),
        json={"activity_ids": [str(mine.id), str(uuid.uuid4())], "justificativa": "Conferi"},
        headers=headers,
    )

    assert response.status_code == 404
    assert status_of(client, mine) == "AGUARDANDO_REVISAO"


@pytest.mark.parametrize("body", [{}, {"justificativa": None}, {"justificativa": ""},
                                  {"justificativa": "   "}])  # fmt: skip
def test_without_a_justification_it_is_422_on_justificativa_and_nothing_is_validated(
    client, admin, headers, chosen, body
):
    mine = draft(client, admin, chosen, "Minha")

    response = client.post(url(chosen), json={"activity_ids": [str(mine.id)], **body},
                           headers=headers)  # fmt: skip

    assert response.status_code == 422
    assert response.json()["detail"][0]["field"] == "justificativa"
    assert status_of(client, mine) == "AGUARDANDO_REVISAO"


def test_it_writes_one_audit_event_per_activity_with_the_justification(
    client, admin, headers, chosen, uow_factory
):
    drafts = [draft(client, admin, chosen, t) for t in ("A", "B", "C")]

    client.post(
        url(chosen),
        json={"activity_ids": [str(a.id) for a in drafts], "justificativa": "Conferi todas"},
        headers=headers,
    )

    with uow_factory() as uow:
        for activity in drafts:
            events = [
                e for e in uow.audit.list_for("activity", str(activity.id))
                if e.justification == "Conferi todas"
            ]  # fmt: skip
            assert len(events) == 1


def test_it_needs_a_session_the_csrf_token_access_and_an_open_process(
    client, make_client, act_as, admin, headers, chosen, reference
):
    mine = draft(client, admin, chosen, "Minha")
    body = {"activity_ids": [str(mine.id)], "justificativa": "Conferi"}
    anonymous = make_client()
    no_csrf = client.post(url(chosen), json=body)
    _, other = act_as("fora@ufpa.br", Role.SECRETARIA, unit_ids=frozenset({reference["IFCH"].id}))
    outsider = client.post(url(chosen), json=body, headers=other)
    _, again = act_as("admin2@ufpa.br", Role.ADMIN)
    close_process(client, again, chosen)
    closed = client.post(url(chosen), json=body, headers=again)

    assert anonymous.post(url(chosen), json=body).status_code == 401
    assert no_csrf.status_code == 403
    assert outsider.status_code == 404
    assert closed.status_code == 409
    assert status_of(client, mine) == "AGUARDANDO_REVISAO"
