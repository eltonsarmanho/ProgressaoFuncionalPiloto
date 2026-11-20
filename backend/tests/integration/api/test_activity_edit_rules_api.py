"""EDT-02, EDT-03, EDT-06, QTD-02, QTD-03: the date inside the interstice and the quantity.

The process of these tests has the interstice 2022-11-23 to 2024-11-23.
"""

import uuid
from datetime import date
from decimal import Decimal

import pytest

from app.application.use_cases.scoring import ActivityData
from app.domain.entities.activity import ActivitySource
from app.domain.rules.scoring_periods import is_yearly_unit

RANGE = "A data deve estar entre 23/11/2022 e 23/11/2024"


@pytest.fixture
def chosen(client, headers, process, scoring_tables):
    body = {"version_id": str(scoring_tables["OFICIAL"].id)}
    response = client.put(
        f"/api/processes/{process['id']}/scoring/table", json=body, headers=headers
    )
    assert response.status_code == 200, response.text
    return process


@pytest.fixture
def yearly_item(scoring_tables):
    """(group, item) of a criterion measured "por ano"."""
    version = scoring_tables["OFICIAL"]
    return next(
        (c.group_number, c.item_number)
        for g in version.groups
        for c in g.criteria
        if is_yearly_unit(c.unit_label)
    )


def activities_url(process):
    return f"/api/processes/{process['id']}/activities"


def body(**kw):
    return {"title": "Orientação de TCC", "group_number": 2, "item_number": 7, **kw}


def errors(response, field):
    assert response.status_code == 422, response.text
    [error] = [e for e in response.json()["detail"] if e["field"] == field]
    return error


def listed(client, process):
    return client.get(activities_url(process)).json()


def created_from_document(client, admin, process, **kw):
    """An activity as the document reading creates it (source SUGERIDA_IA): not reachable by API."""
    user, _ = admin
    fields = {"title": "Lida do documento", "group_number": 2, "item_number": 7, **kw}
    return client.app.state.container.create_activity.execute(
        user, uuid.UUID(process["id"]), ActivityData(**fields), source=ActivitySource.SUGERIDA_IA
    )


# --- the date of a manual creation (EDT-02) ----------------------------------------------------


def test_a_manual_activity_with_a_date_outside_the_interstice_is_422_on_event_date(
    client, headers, chosen
):
    response = client.post(
        activities_url(chosen), json=body(event_date="2020-01-10", quantidade=1), headers=headers
    )

    assert errors(response, "event_date")["message"] == RANGE
    assert listed(client, chosen) == []


@pytest.mark.parametrize("day", ["2022-11-23", "2024-11-23"])
def test_the_first_and_the_last_day_of_the_interstice_are_accepted(client, headers, chosen, day):
    response = client.post(
        activities_url(chosen), json=body(event_date=day, quantidade=1), headers=headers
    )

    assert response.status_code == 201, response.text


@pytest.mark.parametrize("day", ["2022-11-22", "2024-11-24"])
def test_the_day_before_and_the_day_after_the_interstice_are_refused(client, headers, chosen, day):
    response = client.post(
        activities_url(chosen), json=body(event_date=day, quantidade=1), headers=headers
    )

    assert errors(response, "event_date")["message"] == RANGE


def test_a_month_only_date_is_judged_by_its_month(client, headers, chosen):
    inside = client.post(
        activities_url(chosen), json=body(event_date="2022-11", quantidade=1), headers=headers
    )
    outside = client.post(
        activities_url(chosen), json=body(event_date="2022-10", quantidade=1), headers=headers
    )

    assert inside.status_code == 201, inside.text  # November 2022 reaches the 23rd
    assert errors(outside, "event_date")["message"] == RANGE


def test_an_activity_with_no_date_is_still_accepted(client, headers, chosen):
    response = client.post(activities_url(chosen), json=body(quantidade=1), headers=headers)

    assert response.status_code == 201, response.text


# --- the period of an item measured by year (EDT-03) -------------------------------------------


def test_a_yearly_item_accepts_a_period_that_crosses_the_interstice(
    client, headers, chosen, yearly_item
):
    group, item = yearly_item
    payload = body(group_number=group, item_number=item, quantidade=1,
                   period_start="2021-01-01", period_end="2023-01-01")  # fmt: skip

    response = client.post(activities_url(chosen), json=payload, headers=headers)

    assert response.status_code == 201, response.text


def test_a_yearly_item_refuses_a_period_that_ends_before_the_interstice(
    client, headers, chosen, yearly_item
):
    group, item = yearly_item
    payload = body(group_number=group, item_number=item, quantidade=1,
                   period_start="2020-01-01", period_end="2021-12-31")  # fmt: skip

    response = client.post(activities_url(chosen), json=payload, headers=headers)

    assert errors(response, "period_end")["message"] == RANGE
    assert listed(client, chosen) == []


def test_a_yearly_item_refuses_a_period_that_starts_after_the_interstice(
    client, headers, chosen, yearly_item
):
    group, item = yearly_item
    payload = body(group_number=group, item_number=item, quantidade=1,
                   period_start="2025-01-01", period_end="2026-01-01")  # fmt: skip

    response = client.post(activities_url(chosen), json=payload, headers=headers)

    assert errors(response, "period_start")["message"] == RANGE


@pytest.mark.parametrize("start", ["2021-01-01", "2023-01-01"])
def test_a_yearly_item_with_only_a_start_is_open_and_accepted_before_or_inside_the_interstice(
    client, headers, chosen, yearly_item, start
):
    # the period with no end runs to the end of the interstice, so it touches it (EDT-03)
    group, item = yearly_item
    payload = body(group_number=group, item_number=item, quantidade=1, period_start=start)

    response = client.post(activities_url(chosen), json=payload, headers=headers)

    assert response.status_code == 201, response.text
    assert response.json()["period_start"] == start


def test_a_yearly_item_with_only_a_start_after_the_interstice_is_422_on_period_start(
    client, headers, chosen, yearly_item
):
    group, item = yearly_item
    payload = body(group_number=group, item_number=item, quantidade=1, period_start="2025-01-01")

    response = client.post(activities_url(chosen), json=payload, headers=headers)

    assert errors(response, "period_start")["message"] == RANGE
    assert listed(client, chosen) == []


def test_the_edit_of_a_yearly_item_keeps_the_open_period_rule(client, headers, chosen, yearly_item):
    group, item = yearly_item
    first = body(group_number=group, item_number=item, quantidade=1, period_start="2023-01-01")
    created = client.post(activities_url(chosen), json=first, headers=headers).json()
    url = f"/api/activities/{created['id']}"

    before = client.put(
        url, json=first | {"period_start": "2021-01-01", "expected_version": 1}, headers=headers
    )
    after = client.put(
        url, json=first | {"period_start": "2025-01-01", "expected_version": 2}, headers=headers
    )

    assert before.status_code == 200, before.text
    assert before.json()["period_start"] == "2021-01-01"
    assert errors(after, "period_start")["message"] == RANGE
    assert client.get(url).json()["period_start"] == "2021-01-01"


# --- the edit (EDT-02, EDT-06) -----------------------------------------------------------------


def test_editing_to_a_date_outside_the_interstice_is_422_and_keeps_the_activity(
    client, headers, chosen
):
    created = client.post(
        activities_url(chosen), json=body(event_date="2023-05-10", quantidade=1), headers=headers
    ).json()

    response = client.put(
        f"/api/activities/{created['id']}",
        json=body(event_date="2021-05-10", expected_version=1),
        headers=headers,
    )

    assert errors(response, "event_date")["message"] == RANGE
    after = client.get(f"/api/activities/{created['id']}").json()
    assert (after["event_date"], after["version"]) == ("2023-05-10", 1)


def test_editing_a_title_keeps_a_date_that_was_already_outside_and_changing_it_is_refused(
    client, admin, headers, chosen
):
    outside = created_from_document(client, admin, chosen, event_date=date(2020, 1, 10))
    url = f"/api/activities/{outside.id}"
    kept = body(event_date="2020-01-10", title="Título corrigido", expected_version=1)

    same_date = client.put(url, json=kept, headers=headers)
    other_date = client.put(
        url, json=kept | {"event_date": "2021-03-03", "expected_version": 2}, headers=headers
    )
    inside = client.put(
        url, json=kept | {"event_date": "2023-03-03", "expected_version": 2}, headers=headers
    )

    assert same_date.status_code == 200, same_date.text
    assert same_date.json()["title"] == "Título corrigido"
    assert errors(other_date, "event_date")["message"] == RANGE
    assert inside.status_code == 200, inside.text
    assert inside.json()["event_date"] == "2023-03-03"


def test_a_yearly_period_is_checked_on_the_edit_too(client, headers, chosen, yearly_item):
    group, item = yearly_item
    first = body(group_number=group, item_number=item, quantidade=1,
                 period_start="2021-01-01", period_end="2023-01-01")  # fmt: skip
    created = client.post(activities_url(chosen), json=first, headers=headers).json()

    response = client.put(
        f"/api/activities/{created['id']}",
        json=first | {"period_start": "2019-01-01", "period_end": "2020-01-01",
                      "expected_version": 1},
        headers=headers,
    )

    assert errors(response, "period_end")["message"] == RANGE


# --- a date read from a document is never refused (SEC-06) ------------------------------------


def test_an_activity_read_from_a_document_outside_the_interstice_is_created(
    client, admin, headers, chosen
):
    created = created_from_document(client, admin, chosen, event_date=date(2020, 1, 10))

    found = client.get(f"/api/activities/{created.id}")

    assert found.status_code == 200
    assert found.json()["event_date"] == "2020-01-10"
    assert [a["id"] for a in listed(client, chosen)] == [str(created.id)]
    scoring = client.get(f"/api/processes/{chosen['id']}/scoring").json()
    assert scoring["rows"] == []  # not valid: it does not score


# --- the quantity (QTD-02, QTD-03) -------------------------------------------------------------


@pytest.mark.parametrize("quantity", [-1, -0.5, "abc"])
def test_a_negative_or_non_numeric_quantity_is_422_on_quantidade(
    client, headers, chosen, quantity
):
    created = client.post(
        activities_url(chosen), json=body(event_date="2023-05-10", quantidade=1), headers=headers
    ).json()
    url = f"/api/activities/{created['id']}"

    on_create = client.post(
        activities_url(chosen),
        json=body(event_date="2023-05-10", quantidade=quantity),
        headers=headers,
    )
    on_edit = client.put(
        url,
        json=body(event_date="2023-05-10", quantidade=quantity, expected_version=1),
        headers=headers,
    )

    errors(on_create, "quantidade")
    errors(on_edit, "quantidade")
    assert client.get(url).json()["quantidade"] == "1.00"


def test_changing_the_quantity_recalculates_the_points_and_audits_without_a_justification(
    client, headers, chosen, uow_factory
):
    created = client.post(
        activities_url(chosen), json=body(event_date="2023-05-10", quantidade=1), headers=headers
    ).json()
    before = client.get(f"/api/processes/{chosen['id']}/scoring").json()

    response = client.put(
        f"/api/activities/{created['id']}",
        json=body(event_date="2023-05-10", quantidade=3, expected_version=1),
        headers=headers,
    )

    assert response.status_code == 200, response.text
    after = client.get(f"/api/processes/{chosen['id']}/scoring").json()
    assert Decimal(after["total"]) == Decimal(before["total"]) * 3 > 0
    with uow_factory() as uow:
        events = list(uow.audit.list_for("activity", created["id"]))
    update = events[-1]
    assert update.action.value == "UPDATE"
    assert update.justification is None
    assert update.changes["quantity"] == {"before": "1", "after": "3"}
