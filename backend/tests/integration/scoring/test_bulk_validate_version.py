"""SEG-11 (B04): a bulk validation leaves an already validated activity untouched."""

import pytest

from app.application.use_cases import scoring
from app.application.use_cases.scoring import ActivityData
from app.domain.entities.activity import ActivitySource, ActivityStatus


@pytest.fixture
def bulk(world):
    return scoring.BulkValidateActivities(world.uow_factory, world.audit, world.policy)


def draft(world, title):
    return world.create.execute(
        world.admin,
        world.process.id,
        ActivityData(title=title, group_number=3, item_number=4),
        source=ActivitySource.SUGERIDA_IA,
    )


def reload(world, activity):
    with world.uow_factory() as uow:
        return uow.activities.get(activity.id)


def test_an_already_validated_activity_keeps_its_version_and_timestamp(world, bulk):
    pending, done = draft(world, "Pendente"), draft(world, "Ja validada")
    world.change_status.execute(
        world.admin, done.id, ActivityStatus.VALIDADA, done.version, "Antes"
    )
    before = reload(world, done)

    bulk.execute(world.docente, world.process.id, [pending.id, done.id], "Agora")

    after = reload(world, done)
    assert (after.version, after.updated_at) == (before.version, before.updated_at)
    assert reload(world, pending).version == pending.version + 1  # the pending one did change
