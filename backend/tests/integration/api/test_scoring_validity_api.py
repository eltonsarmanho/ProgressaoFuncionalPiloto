"""VAL-01, SEG-01, SEG-04: the Etapa 4 scores only the valid activities, with and without table."""

import uuid
from datetime import date
from decimal import Decimal

import pytest

from app.application.use_cases.scoring import ActivityData
from app.domain.entities.activity import Activity, ActivitySource, ActivityStatus
from app.domain.entities.user import Role
from tests.integration.api.factories import add_professor, process_payload

D = Decimal
INSIDE = date(2023, 5, 10)  # the interstice of the process is 2022-11-23 to 2024-11-23


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
    assert response.status_code == 200, response.text
    return process


def score(client, process):
    response = client.get(f"/api/processes/{process['id']}/scoring")
    assert response.status_code == 200, response.text
    return response.json()


def add_activity(uow_factory, process, **kw):
    kw.setdefault("event_date", INSIDE)
    kw.setdefault("quantity", D(1))
    kw.setdefault("evidence_note", "Declaração")
    with uow_factory() as uow:
        creator = uow.users.get_by_email("admin@ufpa.br")
        activity = Activity(
            id=uuid.uuid4(), process_id=uuid.UUID(process["id"]), created_by=creator.id, **kw
        )
        uow.activities.add(activity)
        uow.commit()
    return activity


def row_ids(body):
    return {r["activity_id"] for r in body["rows"]}


# --- validating scores with no other action (VAL-01) ---------------------------------------


def test_a_validated_co_advisorship_scores_eight_points_with_no_other_action(
    client, admin, headers, chosen
):
    user, _ = admin
    suggested = client.app.state.container.create_activity.execute(
        user,
        uuid.UUID(chosen["id"]),
        ActivityData(
            title="Co-orientação de dissertação de mestrado",
            group_number=2,
            item_number=5,
            event_date=INSIDE,
            quantity=D(1),
        ),
        source=ActivitySource.SUGERIDA_IA,
    )
    assert score(client, chosen)["total"] == "0.00"

    validated = client.post(
        f"/api/activities/{suggested.id}/status",
        json={"status": "VALIDADA", "expected_version": suggested.version},
        headers=headers,
    )

    assert validated.status_code == 200, validated.text
    body = score(client, chosen)
    [row] = body["rows"]
    assert (row["status"], row["unit_points"], row["points"]) == ("PONTUADA", "8.00", "8.00")
    assert body["total"] == "8.00"


# --- the activities that are not valid leave the score (SEG-01) ----------------------------


def test_not_valid_activities_are_in_no_row_and_no_counter(client, chosen, uow_factory):
    valid = add_activity(uow_factory, chosen, title="Válida", group_number=2, item_number=5)
    outside = add_activity(
        uow_factory, chosen, title="Fora", group_number=2, item_number=5,
        event_date=date(2020, 1, 1),
    )  # fmt: skip
    rejected = add_activity(
        uow_factory, chosen, title="Rejeitada", group_number=2, item_number=5,
        status=ActivityStatus.REJEITADA,
    )  # fmt: skip
    short = add_activity(
        uow_factory, chosen, title="Curso curto", group_number=4, item_number=3,
        hours=D("10"),
    )  # fmt: skip

    body = score(client, chosen)

    assert row_ids(body) == {str(valid.id)}
    assert not row_ids(body) & {str(a.id) for a in (outside, rejected, short)}
    assert body["counters"]["activities"] == 1
    assert body["counters"]["not_scored"] == 0
    assert body["total"] == "8.00"


def test_moving_the_date_of_an_activity_inside_includes_it_in_the_next_calculation(
    client, chosen, uow_factory
):
    outside = add_activity(
        uow_factory, chosen, title="Fora", group_number=2, item_number=5,
        event_date=date(2020, 1, 1),
    )  # fmt: skip
    assert score(client, chosen)["rows"] == []

    with uow_factory() as uow:
        stored = uow.activities.get(outside.id)
        stored.event_date = INSIDE
        uow.activities.update(stored, stored.version)
        uow.commit()

    body = score(client, chosen)
    assert row_ids(body) == {str(outside.id)}
    assert body["total"] == "8.00"
    assert body["counters"]["activities"] == 1


# --- without a table (SEG-04) --------------------------------------------------------------


def test_without_a_table_only_the_valid_activities_count(client, process, uow_factory):
    valid = add_activity(uow_factory, process, title="Válida", group_number=2, item_number=5)
    no_category = add_activity(uow_factory, process, title="Sem categoria")
    outside = add_activity(
        uow_factory, process, title="Fora", group_number=2, item_number=5,
        event_date=date(2020, 1, 1),
    )  # fmt: skip
    rejected = add_activity(
        uow_factory, process, title="Rejeitada", group_number=2, item_number=5,
        status=ActivityStatus.REJEITADA,
    )  # fmt: skip

    body = score(client, process)

    assert body["chosen"] is None
    assert row_ids(body) == {str(valid.id), str(no_category.id)}
    assert not row_ids(body) & {str(outside.id), str(rejected.id)}
    assert body["counters"]["activities"] == 2
    assert body["counters"]["not_scored"] == 2
    assert {r["reasons"][0] for r in body["rows"]} == {"SEM_TABELA"}
    assert body["total"] == "0.00"
