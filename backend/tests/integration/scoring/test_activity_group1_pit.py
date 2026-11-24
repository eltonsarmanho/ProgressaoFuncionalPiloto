"""PIT-03, GI-05: informed points are refused on every group I weekly-load criterion, whether
the group is outside the total (PIT hours) or counts in it, in any table version."""

import uuid
from dataclasses import fields
from datetime import date
from decimal import Decimal

import pytest

from app.application.use_cases.scoring import ActivityData
from app.domain.entities.activity import Level
from app.domain.entities.scoring import (
    ScoringCriterion,
    ScoringGroup,
    ScoringMode,
    ScoringTableVersion,
    TableStatus,
)
from app.domain.errors import ValidationFailed
from app.domain.repositories.ports import ScoringTableRecord

D = Decimal


def pit_version(table_id) -> ScoringTableVersion:
    weekly = lambda item, prep: ScoringCriterion(  # noqa: E731
        1, item, f"I.{item}", "horas (PIT)", ScoringMode.CARGA_SEMANAL,
        weeks_per_semester=17, prep_ratio=D(prep),
    )  # fmt: skip
    per_unit = ScoringCriterion(
        2, 7, "II.7", "unidade", ScoringMode.POR_UNIDADE, unit_points=D("5")
    )
    return ScoringTableVersion(
        table_id=table_id,
        name="Versão com PIT",
        valid_from=date(2015, 3, 24),
        valid_to=None,
        norm_reference="Tabela de teste",
        status=TableStatus.OFICIAL,
        groups=(
            ScoringGroup(
                1, "Grupo I", counts_in_total=False, criteria=(weekly(1, "1"), weekly(2, "2"))
            ),
            ScoringGroup(2, "Grupo II", criteria=(per_unit,)),
        ),
        id=uuid.uuid4(),
    )  # fmt: skip


@pytest.fixture
def pit_world(world):
    table = ScoringTableRecord(uuid.uuid4(), "Tabela com PIT", unit_ids=(world.fasi.id,))
    version = pit_version(table.id)
    with world.uow_factory() as uow:
        uow.scoring_tables.add_table(table)
        uow.scoring_tables.add_version(version)
        uow.commit()
    world.choose.execute(world.admin, world.process.id, version.id, None, None)
    return world


def offer(**kw) -> ActivityData:
    kw.setdefault("title", "Disciplina")
    kw.setdefault("group_number", 1)
    kw.setdefault("academic_period", "2023.1")
    kw.setdefault("level", Level.GRADUACAO)
    kw.setdefault("hours", D("68"))
    kw.setdefault("event_date", date(2023, 5, 10))
    return ActivityData(**kw)


def as_data(activity, **changes) -> ActivityData:
    names = {f.name for f in fields(ActivityData)}
    return ActivityData(**{**{n: getattr(activity, n) for n in names}, **changes})


def test_create_with_informed_points_in_group1_is_422_on_points_override(pit_world):
    world = pit_world

    with pytest.raises(ValidationFailed) as error:
        world.create.execute(
            world.admin, world.process.id, offer(points_override=D("24")), "Declaração"
        )

    assert error.value.field == "points_override"
    with world.uow_factory() as uow:
        assert uow.activities.list_for_process(world.process.id) == []


def test_postgraduation_offer_with_informed_points_is_also_refused(pit_world):
    world = pit_world

    with pytest.raises(ValidationFailed) as error:
        world.create.execute(
            world.admin,
            world.process.id,
            offer(level=Level.POS_GRADUACAO, points_override=D("24")),
            "Declaração",
        )

    assert error.value.field == "points_override"


def test_update_adding_informed_points_to_a_group1_activity_is_422(pit_world):
    world = pit_world
    activity = world.create.execute(world.admin, world.process.id, offer())

    with pytest.raises(ValidationFailed) as error:
        world.update.execute(
            world.admin,
            activity.id,
            as_data(activity, points_override=D("24")),
            activity.version,
            "Declaração",
        )

    assert error.value.field == "points_override"
    with world.uow_factory() as uow:
        assert uow.activities.get(activity.id).points_override is None


def test_group1_activity_without_informed_points_is_accepted_and_keeps_its_hours(pit_world):
    world = pit_world

    activity = world.create.execute(world.admin, world.process.id, offer())

    assert activity.points_override is None
    assert (activity.group_number, activity.item_number, activity.hours) == (1, 1, D("68"))
    updated = world.update.execute(
        world.admin, activity.id, as_data(activity, hours=D("34")), activity.version, "Ajuste"
    )
    assert updated.hours == D("34")


def test_other_groups_are_not_affected_by_the_group1_rule(pit_world):
    world = pit_world

    activity = world.create.execute(
        world.admin,
        world.process.id,
        ActivityData(
            title="Orientação", group_number=2, item_number=7, quantity=D("2"),
            event_date=date(2023, 5, 10),
        ),  # fmt: skip
    )

    assert activity.quantity == D("2")
    with pytest.raises(ValidationFailed) as error:  # unchanged rule: only weekly-load criteria
        world.create.execute(
            world.admin,
            world.process.id,
            ActivityData(
                title="Outra", group_number=2, item_number=7, points_override=D("5"),
                event_date=date(2023, 5, 11),
            ),  # fmt: skip
            "x",
        )
    assert error.value.field == "points_override"


@pytest.mark.parametrize("level", [Level.GRADUACAO, Level.POS_GRADUACAO])
def test_create_with_informed_points_in_a_group1_that_counts_in_the_total_is_422(
    points_chosen, level
):
    # GI-05: was "a table that counts points still accepts informed points" (PIT-03 only refused
    # them where group I was outside the total); now refused in any version.
    world = points_chosen

    with pytest.raises(ValidationFailed) as error:
        world.create.execute(
            world.admin,
            world.process.id,
            offer(level=level, points_override=D("24")),
            "Declaração",
        )

    assert error.value.field == "points_override"
    assert error.value.message == (
        "No Grupo I, as horas de PIT são calculadas da carga horária; não há pontos a informar"
    )
    with world.uow_factory() as uow:
        assert uow.activities.list_for_process(world.process.id) == []


def test_update_adding_informed_points_to_a_group1_that_counts_in_the_total_is_422(
    points_chosen,
):
    world = points_chosen
    activity = world.create.execute(world.admin, world.process.id, offer())

    with pytest.raises(ValidationFailed) as error:
        world.update.execute(
            world.admin,
            activity.id,
            as_data(activity, points_override=D("24")),
            activity.version,
            "Declaração",
        )

    assert error.value.field == "points_override"
    with world.uow_factory() as uow:
        assert uow.activities.get(activity.id).points_override is None


def test_group1_offer_without_informed_points_is_accepted_in_a_group1_that_counts(
    points_chosen,
):
    world = points_chosen

    activity = world.create.execute(world.admin, world.process.id, offer())

    assert activity.points_override is None
    assert (activity.group_number, activity.item_number, activity.hours) == (1, 1, D("68"))
