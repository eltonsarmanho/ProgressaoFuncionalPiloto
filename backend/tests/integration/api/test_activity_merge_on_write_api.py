"""DUP-04: creating or editing an activity merges the duplicates in the same write."""

import uuid
from datetime import date

import pytest

from app.domain.entities.activity import Activity, ActivityStatus
from tests.integration.api.generated_support import add_document_row, link_page

TITLE = "Visão Computacional com OpenCV"


@pytest.fixture
def chosen(client, headers, process, scoring_tables):
    body = {"version_id": str(scoring_tables["OFICIAL"].id)}
    response = client.put(
        f"/api/processes/{process['id']}/scoring/table", json=body, headers=headers
    )
    assert response.status_code == 200, response.text
    return process


def activities_url(process):
    return f"/api/processes/{process['id']}/activities"


def payload(title=TITLE, **kw):
    return {
        "title": title,
        "group_number": 2,
        "item_number": 7,
        "quantidade": 1,
        "event_date": "2023-05-10",
        **kw,
    }


def create(client, headers, process, **kw):
    response = client.post(activities_url(process), json=payload(**kw), headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def listed(client, process):
    response = client.get(activities_url(process))
    assert response.status_code == 200, response.text
    return response.json()


def add_draft(uow_factory, process, admin, title=TITLE):
    """A draft inserted straight, so that two of them stay unmerged until a write happens."""
    user, _ = admin
    activity = Activity(
        id=uuid.uuid4(),
        process_id=uuid.UUID(process["id"]),
        created_by=user.id,
        title=title,
        group_number=2,
        item_number=7,
        event_date=date(2023, 5, 10),
        status=ActivityStatus.AGUARDANDO_REVISAO,
    )
    with uow_factory() as uow:
        uow.activities.add(activity)
        uow.commit()
    return {"id": str(activity.id)}


def proofs(client, activity_id):
    return {
        (e["document_id"], e["page"])
        for e in client.get(f"/api/activities/{activity_id}").json()["evidences"]
    }


def test_creating_an_activity_equal_to_another_merges_them_at_once_with_both_proofs(
    client, admin, headers, chosen, uow_factory
):
    user, _ = admin
    first = add_draft(uow_factory, chosen, admin)
    second = add_draft(uow_factory, chosen, admin)
    docs = [add_document_row(uow_factory, chosen, user) for _ in range(2)]
    link_page(uow_factory, user, first, docs[0], 1)
    link_page(uow_factory, user, second, docs[1], 2)
    assert len(listed(client, chosen)) == 2  # nothing merged yet: both were inserted straight

    third = create(client, headers, chosen)

    [only] = listed(client, chosen)
    assert only["id"] == third["id"]  # the validated one stays (a manual activity is validated)
    assert proofs(client, only["id"]) == {
        (str(docs[0].id), 1),
        (str(docs[1].id), 2),
    }


def test_the_response_of_the_create_is_the_activity_that_was_written(
    client, admin, headers, chosen, uow_factory
):
    add_draft(uow_factory, chosen, admin)

    created = create(client, headers, chosen)

    assert created["title"] == TITLE
    assert [a["id"] for a in listed(client, chosen)] == [created["id"]]


def test_editing_the_title_to_equal_another_merges_them(client, headers, chosen):
    older = create(client, headers, chosen, title=TITLE)
    newer = create(client, headers, chosen, title="Outra atividade bem diferente")

    response = client.put(
        f"/api/activities/{newer['id']}",
        json=payload(title=TITLE) | {"expected_version": 1},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert [a["id"] for a in listed(client, chosen)] == [older["id"]]  # both validated: the first


def test_editing_until_it_is_no_longer_a_duplicate_does_not_undo_the_merge(
    client, headers, chosen
):
    kept = create(client, headers, chosen)
    merged = create(client, headers, chosen)
    assert [a["id"] for a in listed(client, chosen)] == [kept["id"]]

    response = client.put(
        f"/api/activities/{kept['id']}",
        json=payload(title="Agora uma atividade totalmente distinta") | {"expected_version": 1},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert [a["id"] for a in listed(client, chosen)] == [kept["id"]]
    assert client.get(f"/api/activities/{merged['id']}").status_code == 200  # the row stays


def test_a_failure_of_the_merge_reverts_the_creation_and_what_the_merge_did(
    client, admin, headers, chosen, uow_factory, monkeypatch
):
    first = add_draft(uow_factory, chosen, admin)
    second = add_draft(uow_factory, chosen, admin)
    merger = client.app.state.container.create_activity._merger
    real = merger.merge_process

    def merge_then_fail(*args, **kwargs):
        real(*args, **kwargs)  # the merge writes its changes, then the step fails
        raise RuntimeError("merge failed")

    monkeypatch.setattr(merger, "merge_process", merge_then_fail)

    with pytest.raises(RuntimeError):
        client.post(activities_url(chosen), json=payload(), headers=headers)

    assert {a["id"] for a in listed(client, chosen)} == {first["id"], second["id"]}


def test_a_failure_of_the_merge_reverts_the_edit(
    client, admin, headers, chosen, uow_factory, monkeypatch
):
    older = create(client, headers, chosen, title="Primeira atividade")
    newer = create(client, headers, chosen, title="Segunda atividade bem diferente")
    merger = client.app.state.container.update_activity._merger

    def fail(*args, **kwargs):
        raise RuntimeError("merge failed")

    monkeypatch.setattr(merger, "merge_process", fail)

    with pytest.raises(RuntimeError):
        client.put(
            f"/api/activities/{newer['id']}",
            json=payload(title="Primeira atividade") | {"expected_version": 1},
            headers=headers,
        )

    after = client.get(f"/api/activities/{newer['id']}").json()
    assert (after["title"], after["version"]) == ("Segunda atividade bem diferente", 1)
    assert {a["id"] for a in listed(client, chosen)} == {older["id"], newer["id"]}
