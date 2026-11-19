"""SEC-02, SEC-06, SEC-07, SEC-08, SEC-09: the listing of the activities says whether each one is
valid and why not, what was merged into it and the points it is expected to score.

The interstice of the process of these tests is 2022-11-23 to 2024-11-23.
"""

from datetime import date
from decimal import Decimal

import pytest

from app.application.services.activity_merge import MergeDuplicateActivities
from app.application.use_cases.scoring import ActivityData
from app.domain.entities.activity import ActivitySource, ActivityStatus
from app.domain.errors import NotFound
from app.domain.rules.activity_validity import InvalidReason, ValidityState

D = Decimal
INSIDE = date(2023, 5, 10)


def add(world, title, group=2, item=7, source=ActivitySource.IMPORTADA, **kw):
    """An imported activity (AGUARDANDO_REVISAO): neither the date rule nor the merge runs."""
    kw.setdefault("event_date", INSIDE)
    kw.setdefault("quantity", D("1"))
    return world.create.execute(
        world.admin,
        world.process.id,
        ActivityData(title=title, group_number=group, item_number=item, **kw),
        source=source,
    )


def listing(world):
    return world.list_activities.execute(world.admin, world.process.id)


def validity_of(world, activity):
    return listing(world).validity[activity.id]


def test_a_rejected_activity_is_not_valid_with_its_reason(official_chosen):
    world = official_chosen
    rejected = add(world, "Rejeitada")
    world.change_status.execute(
        world.admin, rejected.id, ActivityStatus.REJEITADA, rejected.version, None
    )

    validity = validity_of(world, rejected)

    assert (validity.state, validity.reason) == (ValidityState.NAO_VALIDA, InvalidReason.REJEITADA)


def test_an_activity_outside_the_interstice_carries_its_date_and_the_interstice(official_chosen):
    world = official_chosen
    outside = add(world, "Fora", event_date=date(2020, 1, 10))

    validity = validity_of(world, outside)

    assert validity.state is ValidityState.NAO_VALIDA
    assert validity.reason is InvalidReason.FORA_DO_INTERSTICIO
    assert validity.params == {
        "event_date": date(2020, 1, 10),
        "interstice_start": date(2022, 11, 23),
        "interstice_end": date(2024, 11, 23),
    }


def test_insufficient_hours_carry_the_hours_and_the_minimum(official_chosen):
    world = official_chosen
    short = add(world, "Curso curto", group=4, item=4, hours=D("19"), quantity=None)

    validity = validity_of(world, short)

    assert validity.reason is InvalidReason.CARGA_HORARIA_INSUFICIENTE
    assert validity.params == {"hours": D("19"), "min_hours": D("20")}


def test_an_activity_with_no_category_is_valid_and_needs_one(official_chosen):
    world = official_chosen
    bare = add(world, "Sem categoria", group=None, item=None)

    validity = validity_of(world, bare)

    assert validity.state is ValidityState.VALIDA
    assert validity.needs_category is True
    assert listing(world).predicted_points.get(bare.id) is None


def test_the_predicted_points_come_before_the_validation_and_stay_empty_without_a_category(
    official_chosen,
):
    world = official_chosen
    waiting = add(world, "Aguardando", quantity=D("3"))
    bare = add(world, "Sem categoria", group=None, item=None)
    assert waiting.status is ActivityStatus.AGUARDANDO_REVISAO

    described = listing(world)

    assert described.predicted_points[waiting.id] == D("15")  # 3 x 5 points of II.7
    assert described.predicted_points.get(bare.id) is None


def test_the_predicted_points_of_a_validated_activity_are_the_ones_it_scores(official_chosen):
    world = official_chosen
    done = add(world, "Validada", quantity=D("2"))
    world.change_status.execute(world.admin, done.id, ActivityStatus.VALIDADA, done.version, None)

    assert listing(world).predicted_points[done.id] == D("10")


def test_a_not_valid_activity_has_no_predicted_points(official_chosen):
    world = official_chosen
    outside = add(world, "Fora", event_date=date(2020, 1, 10))

    assert listing(world).predicted_points.get(outside.id) is None


def test_the_merged_activities_leave_the_list_and_the_kept_one_lists_them(official_chosen):
    world = official_chosen
    kept = add(world, "Visão Computacional com OpenCV")
    twin = add(world, "Visão Computacional com OpenCV")
    other = add(world, "Atividade bem diferente", event_date=date(2023, 8, 1))
    with world.uow_factory() as uow:
        MergeDuplicateActivities(world.audit).merge_process(uow, world.process.id, world.admin.id)
        uow.commit()

    described = listing(world)

    assert [a.id for a in described.activities] == [kept.id, other.id]
    assert [a.id for a in described.merged[kept.id]] == [twin.id]
    assert twin.id not in described.validity
    assert other.id not in described.merged


def test_correcting_a_not_valid_activity_makes_the_next_listing_valid(official_chosen):
    world = official_chosen
    outside = add(world, "Fora", event_date=date(2020, 1, 10))
    assert validity_of(world, outside).state is ValidityState.NAO_VALIDA

    world.update.execute(
        world.admin,
        outside.id,
        ActivityData(
            title="Fora", group_number=2, item_number=7, quantity=D("1"), event_date=INSIDE
        ),
        outside.version,
        None,
    )

    assert validity_of(world, outside).state is ValidityState.VALIDA


def test_reopening_a_rejected_activity_returns_it_to_waiting_and_valid(official_chosen):
    world = official_chosen
    rejected = add(world, "Rejeitada")
    rejected = world.change_status.execute(
        world.admin, rejected.id, ActivityStatus.REJEITADA, rejected.version, None
    )

    world.change_status.execute(
        world.admin, rejected.id, ActivityStatus.AGUARDANDO_REVISAO, rejected.version, None
    )

    [only] = listing(world).activities
    assert only.status is ActivityStatus.AGUARDANDO_REVISAO
    assert validity_of(world, only).state is ValidityState.VALIDA


def test_without_a_table_the_validity_leaves_out_hours_and_group(world):
    short = add(world, "Curso curto", group=4, item=4, hours=D("19"), quantity=None)
    outside = add(world, "Fora", event_date=date(2020, 1, 10))
    bare = add(world, "Sem categoria", group=None, item=None)

    described = listing(world)

    assert described.validity[short.id].state is ValidityState.VALIDA  # hours need the table
    assert described.validity[outside.id].reason is InvalidReason.FORA_DO_INTERSTICIO
    assert described.validity[bare.id].needs_category is True
    assert described.predicted_points.get(short.id) is None  # no table, nothing to predict


def test_the_filters_apply_to_the_listing_but_not_to_the_validity(official_chosen):
    world = official_chosen
    inside = add(world, "Dentro")
    add(world, "Em outro grupo", group=3, item=4, event_date=date(2023, 8, 1))

    described = world.list_activities.execute(world.admin, world.process.id, group_number=2)

    assert [a.id for a in described.activities] == [inside.id]
    assert described.validity[inside.id].state is ValidityState.VALIDA


def test_one_activity_is_described_like_in_the_list(official_chosen):
    world = official_chosen
    outside = add(world, "Fora", event_date=date(2020, 1, 10))
    listed_validity = validity_of(world, outside)

    described = world.get_activity.execute(world.admin, outside.id)

    assert [a.id for a in described.activities] == [outside.id]
    assert described.validity[outside.id] == listed_validity


def test_describing_an_activity_outside_the_access_is_not_found(official_chosen):
    world = official_chosen
    activity = add(world, "Minha")

    with pytest.raises(NotFound):
        world.get_activity.execute(world.other_docente, activity.id)
