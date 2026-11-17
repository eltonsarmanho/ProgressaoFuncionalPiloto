"""ATV-12, ATV-14: listing the activities of a process with filters and order."""

from datetime import date
from uuid import uuid4

import pytest

from app.application.use_cases.scoring import ActivityData
from app.domain.entities.activity import ActivityStatus
from app.domain.errors import NotFound


@pytest.fixture
def listed(official_chosen):
    """Six activities created out of order; returns title -> id."""
    world = official_chosen
    specs = [
        ("sem classificação", None, None, date(2023, 1, 5)),
        ("III.2", 3, 2, date(2023, 2, 1)),
        ("II.8 tardia", 2, 8, date(2023, 9, 1)),
        ("II.7 tardia", 2, 7, date(2023, 8, 1)),
        ("II.7 cedo", 2, 7, date(2023, 3, 1)),
        ("II.7 sem data", 2, 7, None),
    ]
    ids = {}
    for title, group, item, day in specs:
        activity = world.create.execute(
            world.admin,
            world.process.id,
            ActivityData(title=title, group_number=group, item_number=item, event_date=day),
        )
        ids[title] = activity.id
    world.change_status.execute(
        world.admin,
        ids["II.7 cedo"],
        ActivityStatus.REJEITADA,
        1,
        "Duplicada na declaração",
    )
    world.ids = ids
    return world


def titles(activities):
    return [a.title for a in activities]


def test_lists_every_activity_ordered_by_group_item_and_date(listed):
    world = listed

    result = world.list_activities.execute(world.admin, world.process.id)

    assert titles(result) == [
        "II.7 cedo",
        "II.7 tardia",
        "II.7 sem data",
        "II.8 tardia",
        "III.2",
        "sem classificação",
    ]


def test_filters_by_group(listed):
    result = listed.list_activities.execute(listed.admin, listed.process.id, group_number=2)

    assert titles(result) == ["II.7 cedo", "II.7 tardia", "II.7 sem data", "II.8 tardia"]


def test_filters_by_status(listed):
    result = listed.list_activities.execute(
        listed.admin, listed.process.id, status=ActivityStatus.REJEITADA
    )

    assert titles(result) == ["II.7 cedo"]


def test_filters_combine(listed):
    world = listed

    validated_in_2 = world.list_activities.execute(
        world.admin, world.process.id, group_number=2, status=ActivityStatus.VALIDADA
    )
    rejected_in_3 = world.list_activities.execute(
        world.admin, world.process.id, group_number=3, status=ActivityStatus.REJEITADA
    )

    assert titles(validated_in_2) == ["II.7 tardia", "II.7 sem data", "II.8 tardia"]
    assert rejected_in_3 == []


def test_only_activities_of_that_process_are_listed(listed, add_process):
    other = add_process()

    assert listed.list_activities.execute(listed.admin, other.id) == []


@pytest.mark.parametrize("actor", ["other_docente", "other_secretaria"])
def test_process_outside_access_is_not_found(listed, actor):
    with pytest.raises(NotFound):
        listed.list_activities.execute(getattr(listed, actor), listed.process.id)


def test_owner_docente_and_unit_secretaria_may_list(listed):
    for actor in (listed.docente, listed.secretaria):
        assert len(listed.list_activities.execute(actor, listed.process.id)) == 6


def test_unknown_process_is_not_found(listed):
    with pytest.raises(NotFound):
        listed.list_activities.execute(listed.admin, uuid4())
