"""VAL-04: the batch validates what can be validated and lists what it skipped."""

from datetime import date

import pytest

from app.application.use_cases import scoring
from app.application.use_cases.scoring import ActivityData
from app.domain.entities.activity import ActivitySource, ActivityStatus
from app.domain.errors import NotFound, StaleVersion
from tests.integration.scoring.test_bulk_validate import edit_elsewhere, racing_factory


@pytest.fixture
def bulk(world):
    return scoring.BulkValidateActivities(world.uow_factory, world.audit, world.policy)


def draft(world, title, category=(3, 4), event_date=date(2023, 5, 10), **kw):
    group, item = category if category else (None, None)
    return world.create.execute(
        world.admin,
        world.process.id,
        ActivityData(
            title=title, group_number=group, item_number=item, event_date=event_date, **kw
        ),
        source=ActivitySource.SUGERIDA_IA,
    )


def reload(world, activity):
    with world.uow_factory() as uow:
        return uow.activities.get(activity.id)


def run(world, bulk, activities):
    return bulk.execute(world.docente, world.process.id, [a.id for a in activities], None)


def test_three_with_a_category_are_validated_and_two_without_are_skipped(
    world, official_chosen, bulk
):
    categorized = [draft(world, f"Com categoria {n}") for n in range(3)]
    uncategorized = [draft(world, f"Sem categoria {n}", category=None) for n in range(2)]

    result = run(world, bulk, categorized + uncategorized)

    assert [a.id for a in result.activities] == [a.id for a in categorized]
    assert [a.status for a in result.activities] == [ActivityStatus.VALIDADA] * 3
    assert [(s.id, s.reason) for s in result.skipped] == [
        (a.id, "SEM_CATEGORIA") for a in uncategorized
    ]
    for activity in uncategorized:
        assert reload(world, activity).status is ActivityStatus.AGUARDANDO_REVISAO


def test_a_not_valid_activity_is_skipped_with_the_reason_of_its_validity(
    world, official_chosen, bulk
):
    fine = draft(world, "Dentro do interstício")
    outside = draft(world, "Fora do interstício", event_date=date(2020, 1, 10))
    short = draft(world, "Curso curto", category=(4, 4), hours=19)

    result = run(world, bulk, [fine, outside, short])

    assert [a.id for a in result.activities] == [fine.id]
    assert [(s.id, s.reason) for s in result.skipped] == [
        (outside.id, "FORA_DO_INTERSTICIO"),
        (short.id, "CARGA_HORARIA_INSUFICIENTE"),
    ]
    assert reload(world, outside).status is ActivityStatus.AGUARDANDO_REVISAO
    assert reload(world, short).status is ActivityStatus.AGUARDANDO_REVISAO


def test_a_rejected_activity_is_skipped_with_its_reason(world, official_chosen, bulk):
    rejected = draft(world, "Rejeitada")
    world.change_status.execute(
        world.admin, rejected.id, ActivityStatus.REJEITADA, rejected.version, None
    )

    result = run(world, bulk, [reload(world, rejected)])

    assert result.activities == []
    assert [(s.id, s.reason) for s in result.skipped] == [(rejected.id, "REJEITADA")]


def test_the_batch_without_a_table_skips_only_what_has_no_category(world, bulk):
    with_category = draft(world, "Com categoria")
    without = draft(world, "Sem categoria", category=None)

    result = run(world, bulk, [with_category, without])

    assert [a.id for a in result.activities] == [with_category.id]
    assert [(s.id, s.reason) for s in result.skipped] == [(without.id, "SEM_CATEGORIA")]


def test_a_skipped_activity_gets_no_audit_event(world, official_chosen, bulk):
    uncategorized = draft(world, "Sem categoria", category=None)

    run(world, bulk, [uncategorized])

    with world.uow_factory() as uow:
        assert len(list(uow.audit.list_for("activity", str(uncategorized.id)))) == 1


def test_a_stale_version_validates_none_even_with_skipped_ones(world, official_chosen):
    good = draft(world, "Boa")
    other_good = draft(world, "Outra boa")
    uncategorized = draft(world, "Sem categoria", category=None)
    batch = scoring.BulkValidateActivities(
        racing_factory(world, lambda: edit_elsewhere(world, other_good)),
        world.audit,
        world.policy,
    )

    with pytest.raises(StaleVersion):
        run(world, batch, [good, other_good, uncategorized])

    assert reload(world, good).status is ActivityStatus.AGUARDANDO_REVISAO
    assert reload(world, other_good).status is ActivityStatus.AGUARDANDO_REVISAO


def test_an_activity_of_another_process_is_404_and_validates_none(
    world, official_chosen, bulk, add_process
):
    mine = draft(world, "Minha")
    foreign = world.create.execute(
        world.admin,
        add_process().id,
        ActivityData(title="Alheia", group_number=3, item_number=4),
        source=ActivitySource.SUGERIDA_IA,
    )

    with pytest.raises(NotFound):
        run(world, bulk, [mine, foreign])

    assert reload(world, mine).status is ActivityStatus.AGUARDANDO_REVISAO
