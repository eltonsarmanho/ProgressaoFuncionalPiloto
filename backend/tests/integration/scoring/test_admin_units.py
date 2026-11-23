"""GTAB-43: a unit that has a version of the table in use cannot be taken out of the table."""

import uuid
from types import SimpleNamespace

import pytest

from app.application.use_cases.scoring_admin import TABLE_ENTITY, SetTableUnits
from app.application.use_cases.scoring_defaults import SetUnitDefaultVersion
from app.domain.entities.audit import AuditAction
from app.domain.errors import Conflict, Forbidden, NotFound, ValidationFailed
from tests.support.races import Gate, Worker, hooked_factory, wait_until_blocked


@pytest.fixture
def uc(world):
    return SimpleNamespace(
        units=SetTableUnits(world.uow_factory, world.audit),
        mark=SetUnitDefaultVersion(world.uow_factory, world.audit),
    )


def table_id(world):
    return world.official_version.table_id


def units_of(world, table=None):
    with world.uow_factory() as uow:
        return set(uow.scoring_tables.get_table(table or table_id(world)).unit_ids)


def update_events(world, table=None):
    with world.uow_factory() as uow:
        events = uow.audit.list_for(TABLE_ENTITY, str(table or table_id(world)))
    return [e for e in events if e.action is AuditAction.UPDATE]


def test_taking_out_the_unit_that_has_the_version_in_use_is_409_and_the_units_stay(world, uc):
    uc.mark.execute(world.admin, world.fasi.id, world.official_version.id)

    with pytest.raises(Conflict) as refused:
        uc.units.execute(world.admin, table_id(world), [world.ifch.id])

    assert refused.value.code == "UNIDADE_COM_VERSAO_EM_USO"
    assert str(refused.value) == (
        "A tabela tem versão em uso da unidade FASI; desmarque a versão antes de retirá-la"
    )
    assert units_of(world) == {world.fasi.id, world.ifch.id}
    assert update_events(world) == []


def test_the_text_lists_every_unit_taken_out_that_has_the_version_in_use(world, uc):
    uc.mark.execute(world.admin, world.ifch.id, world.official_version.id)
    uc.mark.execute(world.admin, world.fasi.id, world.official_version.id)

    with pytest.raises(Conflict) as refused:
        uc.units.execute(world.admin, table_id(world), [])

    assert refused.value.code == "UNIDADE_COM_VERSAO_EM_USO"
    assert str(refused.value) == (
        "A tabela tem versão em uso das unidades FASI, IFCH; desmarque a versão antes de "
        "retirá-las"
    )
    assert units_of(world) == {world.fasi.id, world.ifch.id}


def test_taking_out_a_unit_without_a_mark_works_and_keeps_the_marked_one(world, uc):
    uc.mark.execute(world.admin, world.fasi.id, world.official_version.id)

    view = uc.units.execute(world.admin, table_id(world), [world.fasi.id])

    assert set(view.table.unit_ids) == {world.fasi.id}
    assert units_of(world) == {world.fasi.id}
    (event,) = update_events(world)
    assert event.user_id == world.admin.id


def test_a_mark_that_belongs_to_another_table_does_not_block_taking_the_unit_out(world, uc):
    uc.units.execute(world.admin, world.other_version.table_id, [world.fasi.id])
    uc.mark.execute(world.admin, world.fasi.id, world.other_version.id)

    uc.units.execute(world.admin, table_id(world), [world.ifch.id])

    assert units_of(world) == {world.ifch.id}
    with world.uow_factory() as uow:
        assert uow.scoring_tables.get_unit_default(world.fasi.id).version_id == (
            world.other_version.id
        )


def test_adding_units_works_as_before(world, uc):
    other = world.other_version.table_id

    uc.units.execute(world.admin, other, [world.fasi.id, world.ifch.id])

    assert units_of(world, other) == {world.fasi.id, world.ifch.id}


def test_a_non_admin_gets_403_and_an_unknown_table_404(world, uc):
    uc.mark.execute(world.admin, world.fasi.id, world.official_version.id)
    for actor in (world.docente, world.secretaria):
        with pytest.raises(Forbidden):
            uc.units.execute(actor, table_id(world), [])
    with pytest.raises(NotFound):
        uc.units.execute(world.admin, uuid.uuid4(), [world.fasi.id])

    assert units_of(world) == {world.fasi.id, world.ifch.id}


def test_an_unknown_unit_is_still_422_on_unit_ids(world, uc):
    with pytest.raises(ValidationFailed) as refused:
        uc.units.execute(world.admin, table_id(world), [uuid.uuid4()])

    assert refused.value.field == "unit_ids"


def test_taking_the_unit_out_while_a_version_is_being_marked_refuses_the_removal(world, engine):
    gate = Gate()
    marking_factory = hooked_factory(engine, ("set_unit_default",), lambda _name: gate.hold())
    marking = Worker(
        lambda: SetUnitDefaultVersion(marking_factory, world.audit).execute(
            world.admin, world.fasi.id, world.official_version.id
        )
    ).start()
    gate.wait_reached()  # the mark is written and holds the lock of the table, not committed
    removal = Worker(
        lambda: SetTableUnits(world.uow_factory, world.audit).execute(
            world.admin, table_id(world), [world.ifch.id]
        )
    ).start()
    wait_until_blocked(engine)

    gate.release()
    marking.join()
    removal.join()

    assert marking.error is None
    assert isinstance(removal.error, Conflict)
    assert removal.error.code == "UNIDADE_COM_VERSAO_EM_USO"
    assert units_of(world) == {world.fasi.id, world.ifch.id}
    with world.uow_factory() as uow:
        assert uow.scoring_tables.get_unit_default(world.fasi.id) is not None


def test_marking_while_the_unit_is_being_taken_out_refuses_the_mark(world, engine):
    gate = Gate()
    removal_factory = hooked_factory(engine, ("set_table_units",), lambda _name: gate.hold())
    removal = Worker(
        lambda: SetTableUnits(removal_factory, world.audit).execute(
            world.admin, table_id(world), [world.ifch.id]
        )
    ).start()
    gate.wait_reached()  # the unit is out and the table is locked, not committed
    marking = Worker(
        lambda: SetUnitDefaultVersion(world.uow_factory, world.audit).execute(
            world.admin, world.fasi.id, world.official_version.id
        )
    ).start()
    wait_until_blocked(engine)

    gate.release()
    removal.join()
    marking.join()

    assert removal.error is None
    assert isinstance(marking.error, ValidationFailed)
    assert marking.error.field == "unit_id"
    assert units_of(world) == {world.ifch.id}
    with world.uow_factory() as uow:
        assert uow.scoring_tables.get_unit_default(world.fasi.id) is None
