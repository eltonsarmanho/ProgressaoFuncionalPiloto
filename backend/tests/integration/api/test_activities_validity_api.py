"""SEC-02, SEC-06, SEC-08, SEG-03: the list and the read of an activity carry the validity, the
merged activities and the predicted points.

The interstice of the process is 2022-11-23 to 2024-11-23.
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.domain.entities.activity import Activity, ActivityStatus
from app.domain.entities.user import Role

D = Decimal
INSIDE = date(2023, 5, 10)


@pytest.fixture
def chosen(client, headers, process, scoring_tables):
    body = {"version_id": str(scoring_tables["OFICIAL"].id)}
    response = client.put(
        f"/api/processes/{process['id']}/scoring/table", json=body, headers=headers
    )
    assert response.status_code == 200, response.text
    return process


def add_activity(uow_factory, admin, process, **kw):
    user, _ = admin
    fields = {
        "title": "Orientação",
        "group_number": 2,
        "item_number": 7,
        "event_date": INSIDE,
        "quantity": D(1),
        "status": ActivityStatus.AGUARDANDO_REVISAO,
        **kw,
    }
    activity = Activity(
        id=uuid.uuid4(), process_id=uuid.UUID(process["id"]), created_by=user.id, **fields
    )
    with uow_factory() as uow:
        uow.activities.add(activity)
        uow.commit()
    return activity


def activities_url(process):
    return f"/api/processes/{process['id']}/activities"


def listed(client, process):
    response = client.get(activities_url(process))
    assert response.status_code == 200, response.text
    return response.json()


def test_a_process_with_120_activities_lists_all_of_them_with_their_validity(
    client, admin, chosen, uow_factory
):
    for n in range(110):
        add_activity(
            uow_factory, admin, chosen, title=f"Atividade número {n} distinta",
            event_date=INSIDE + timedelta(days=n % 300 + n),
        )  # fmt: skip
    outside = [
        add_activity(
            uow_factory, admin, chosen, title=f"Atividade fora {n} distinta",
            event_date=date(2020, 1, 1) + timedelta(days=n * 40),
        )
        for n in range(10)
    ]  # fmt: skip

    body = listed(client, chosen)

    assert len(body) == 120
    by_id = {a["id"]: a for a in body}
    not_valid = {i for i, a in by_id.items() if a["validity"]["state"] == "NAO_VALIDA"}
    assert not_valid == {str(a.id) for a in outside}
    one = by_id[str(outside[0].id)]["validity"]
    assert one["reason"] == "FORA_DO_INTERSTICIO"
    assert one["params"]["interstice_start"] == "2022-11-23"
    assert one["params"]["interstice_end"] == "2024-11-23"
    assert one["params"]["event_date"] == "2020-01-01"


def test_a_merged_activity_is_not_listed_and_the_kept_one_lists_it(
    client, admin, headers, chosen, uow_factory
):
    kept = add_activity(uow_factory, admin, chosen, title="Visão Computacional com OpenCV")
    twin = add_activity(uow_factory, admin, chosen, title="Visão Computacional com OpenCV")
    client.post(f"{activities_url(chosen)}/merge-duplicates", headers=headers)

    body = listed(client, chosen)

    [only] = body
    assert only["id"] == str(kept.id)
    assert only["merged"] == [{"id": str(twin.id), "title": "Visão Computacional com OpenCV"}]


def test_the_read_of_one_activity_has_the_same_fields_as_the_list(
    client, admin, chosen, uow_factory
):
    waiting = add_activity(uow_factory, admin, chosen, quantity=D(3))
    add_activity(
        uow_factory, admin, chosen, title="Fora", event_date=date(2020, 1, 1)
    )

    [from_list] = [a for a in listed(client, chosen) if a["id"] == str(waiting.id)]
    read = client.get(f"/api/activities/{waiting.id}")

    assert read.status_code == 200, read.text
    assert read.json() == from_list
    assert from_list["validity"]["state"] == "VALIDA"
    assert from_list["predicted_points"] == "15.00"


def test_an_activity_without_a_category_needs_one_and_has_no_prediction(
    client, admin, chosen, uow_factory
):
    add_activity(uow_factory, admin, chosen, group_number=None, item_number=None)

    [body] = listed(client, chosen)

    assert body["validity"] == {
        "state": "VALIDA", "reason": None, "needs_category": True, "params": {},
    }  # fmt: skip
    assert body["predicted_points"] is None


def test_a_process_outside_the_access_is_404_for_the_list_and_the_read(
    client, act_as, reference, admin, chosen, uow_factory
):
    activity = add_activity(uow_factory, admin, chosen)
    _, other = act_as(
        "sec.ifch@ufpa.br", Role.SECRETARIA, unit_ids=frozenset({reference["IFCH"].id})
    )

    assert client.get(activities_url(chosen), headers=other).status_code == 404
    assert client.get(f"/api/activities/{activity.id}", headers=other).status_code == 404


def test_validating_a_co_advisorship_scores_eight_points_and_the_list_predicted_them_before(
    client, admin, headers, chosen, uow_factory
):
    draft = add_activity(
        uow_factory, admin, chosen, title="Co-orientação de dissertação de mestrado",
        group_number=2, item_number=5,
    )  # fmt: skip
    [before] = listed(client, chosen)
    assert before["predicted_points"] == "8.00"
    assert client.get(f"/api/processes/{chosen['id']}/scoring").json()["total"] == "0.00"

    validated = client.post(
        f"/api/activities/{draft.id}/status",
        json={"status": "VALIDADA", "expected_version": draft.version},
        headers=headers,
    )

    assert validated.status_code == 200, validated.text
    assert client.get(f"/api/processes/{chosen['id']}/scoring").json()["total"] == "8.00"
    [after] = listed(client, chosen)
    assert (after["status"], after["predicted_points"]) == ("VALIDADA", "8.00")
