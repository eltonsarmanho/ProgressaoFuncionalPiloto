"""GTAB-02, GTAB-03, GTAB-04, GTAB-24: mark and clear the in-use version of a unit."""

import uuid
from dataclasses import replace
from types import SimpleNamespace

import pytest

from app.application.use_cases.scoring_defaults import (
    UNIT_DEFAULT_ENTITY,
    ClearUnitDefaultVersion,
    SetUnitDefaultVersion,
)
from app.domain.entities.audit import AuditAction
from app.domain.errors import Conflict, Forbidden, NotFound, ValidationFailed
from app.domain.repositories.ports import ScoringTableRecord
from tests.support.races import Gate, Worker, hooked_factory, wait_until_blocked


@pytest.fixture
def uc(world):
    return SimpleNamespace(
        set=SetUnitDefaultVersion(world.uow_factory, world.audit),
        clear=ClearUnitDefaultVersion(world.uow_factory, world.audit),
    )


def second_official_version(world, name="Versão B"):
    """Another version of the official table (associated with FASI and IFCH)."""
    version = replace(
        world.official_version, id=uuid.uuid4(), name=name, superseded_by_id=None
    )
    with world.uow_factory() as uow:
        uow.scoring_tables.add_version(version)
        uow.commit()
    return version


def version_of_another_table(world, unit, name="Tabela Sintética B"):
    """A version of a table of its own (so no table lock is shared), associated with the unit."""
    table = ScoringTableRecord(uuid.uuid4(), name, unit_ids=(unit.id,))
    version = replace(
        world.official_version,
        id=uuid.uuid4(),
        table_id=table.id,
        name=f"{name} v1",
        superseded_by_id=None,
    )
    with world.uow_factory() as uow:
        uow.scoring_tables.add_table(table)
        uow.scoring_tables.add_version(version)
        uow.commit()
    return version


def mark_of(world, unit):
    with world.uow_factory() as uow:
        found = uow.scoring_tables.get_unit_default(unit.id)
    return found.version_id if found else None


def events_of(world, unit):
    with world.uow_factory() as uow:
        return list(uow.audit.list_for(UNIT_DEFAULT_ENTITY, str(unit.id)))


def test_the_admin_marks_a_version_and_the_event_is_a_create_with_the_user(world, uc):
    uc.set.execute(world.admin, world.fasi.id, world.official_version.id)

    assert mark_of(world, world.fasi) == world.official_version.id
    (event,) = events_of(world, world.fasi)
    assert event.action is AuditAction.CREATE
    assert event.user_id == world.admin.id
    assert event.entity == "unit_scoring_default"
    assert event.entity_id == str(world.fasi.id)
    assert event.changes == {
        "version_id": {"before": None, "after": str(world.official_version.id)}
    }


def test_marking_another_version_swaps_the_mark_with_an_update_of_before_and_after(world, uc):
    second = second_official_version(world)
    uc.set.execute(world.admin, world.fasi.id, world.official_version.id)

    uc.set.execute(world.admin, world.fasi.id, second.id)

    assert mark_of(world, world.fasi) == second.id
    created, updated = events_of(world, world.fasi)
    assert (created.action, updated.action) == (AuditAction.CREATE, AuditAction.UPDATE)
    assert updated.user_id == world.admin.id
    assert updated.changes == {
        "version_id": {"before": str(world.official_version.id), "after": str(second.id)}
    }


def test_marking_the_same_version_again_writes_no_new_event(world, uc):
    uc.set.execute(world.admin, world.fasi.id, world.official_version.id)

    uc.set.execute(world.admin, world.fasi.id, world.official_version.id)

    assert len(events_of(world, world.fasi)) == 1
    assert mark_of(world, world.fasi) == world.official_version.id


def test_the_marks_of_two_units_are_independent(world, uc):
    uc.set.execute(world.admin, world.fasi.id, world.official_version.id)

    assert mark_of(world, world.ifch) is None
    assert events_of(world, world.ifch) == []


def test_clearing_removes_the_mark_with_a_delete_event_and_clearing_again_writes_none(world, uc):
    uc.set.execute(world.admin, world.fasi.id, world.official_version.id)

    uc.clear.execute(world.admin, world.fasi.id)

    assert mark_of(world, world.fasi) is None
    created, deleted = events_of(world, world.fasi)
    assert deleted.action is AuditAction.DELETE
    assert deleted.user_id == world.admin.id
    assert deleted.changes == {
        "version_id": {"before": str(world.official_version.id), "after": None}
    }

    uc.clear.execute(world.admin, world.fasi.id)

    assert len(events_of(world, world.fasi)) == 2


def test_clearing_a_unit_that_has_no_mark_writes_no_event(world, uc):
    uc.clear.execute(world.admin, world.ifch.id)

    assert events_of(world, world.ifch) == []
    assert mark_of(world, world.ifch) is None


def test_a_non_admin_gets_403_to_mark_and_to_clear_and_nothing_changes(world, uc):
    uc.set.execute(world.admin, world.fasi.id, world.official_version.id)
    for actor in (world.docente, world.secretaria):
        with pytest.raises(Forbidden):
            uc.set.execute(actor, world.fasi.id, world.official_version.id)
        with pytest.raises(Forbidden):
            uc.clear.execute(actor, world.fasi.id)

    assert mark_of(world, world.fasi) == world.official_version.id
    assert len(events_of(world, world.fasi)) == 1


def test_the_403_comes_before_the_404_of_the_version(world, uc):
    with pytest.raises(Forbidden):
        uc.set.execute(world.docente, world.fasi.id, uuid.uuid4())


def test_an_unknown_version_is_404(world, uc):
    with pytest.raises(NotFound):
        uc.set.execute(world.admin, world.fasi.id, uuid.uuid4())


def test_the_404_of_the_version_comes_before_the_422_of_the_unit(world, uc):
    with pytest.raises(NotFound):
        uc.set.execute(world.admin, uuid.uuid4(), uuid.uuid4())


def test_an_unknown_unit_is_422_on_unit_id(world, uc):
    with pytest.raises(ValidationFailed) as refused:
        uc.set.execute(world.admin, uuid.uuid4(), world.official_version.id)

    assert refused.value.field == "unit_id"


def test_an_archived_unit_is_422_on_unit_id(world, uc):
    with world.uow_factory() as uow:
        uow.units.update(replace(uow.units.get(world.fasi.id), archived=True))
        uow.commit()

    with pytest.raises(ValidationFailed) as refused:
        uc.set.execute(world.admin, world.fasi.id, world.official_version.id)

    assert refused.value.field == "unit_id"
    assert mark_of(world, world.fasi) is None


def test_a_table_not_associated_with_the_unit_is_422_on_unit_id(world, uc):
    with pytest.raises(ValidationFailed) as refused:
        uc.set.execute(world.admin, world.fasi.id, world.other_version.id)  # the table has no unit

    assert refused.value.field == "unit_id"
    assert mark_of(world, world.fasi) is None
    assert events_of(world, world.fasi) == []


def test_a_superseded_version_is_409_versao_substituida(world, uc):
    second = second_official_version(world)
    with world.uow_factory() as uow:
        uow.scoring_tables.set_superseded(world.official_version.id, second.id)
        uow.commit()

    with pytest.raises(Conflict) as refused:
        uc.set.execute(world.admin, world.fasi.id, world.official_version.id)

    assert refused.value.code == "VERSAO_SUBSTITUIDA"
    assert mark_of(world, world.fasi) is None


def test_a_version_of_an_archived_table_is_409_tabela_arquivada(world, uc):
    with world.uow_factory() as uow:
        uow.scoring_tables.set_table_archived(world.official_version.table_id, True)
        uow.commit()

    with pytest.raises(Conflict) as refused:
        uc.set.execute(world.admin, world.fasi.id, world.official_version.id)

    assert refused.value.code == "TABELA_ARQUIVADA"
    assert mark_of(world, world.fasi) is None


def test_a_table_outside_the_unit_that_is_also_archived_and_superseded_gets_the_422_first(
    world, uc
):
    with world.uow_factory() as uow:
        uow.scoring_tables.set_table_archived(world.other_version.table_id, True)
        uow.scoring_tables.set_superseded(world.other_version.id, world.official_version.id)
        uow.commit()

    with pytest.raises(ValidationFailed) as refused:
        uc.set.execute(world.admin, world.fasi.id, world.other_version.id)

    assert refused.value.field == "unit_id"


def test_a_superseded_version_of_an_archived_table_gets_the_superseded_code_first(world, uc):
    second = second_official_version(world)
    with world.uow_factory() as uow:
        uow.scoring_tables.set_superseded(world.official_version.id, second.id)
        uow.scoring_tables.set_table_archived(world.official_version.table_id, True)
        uow.commit()

    with pytest.raises(Conflict) as refused:
        uc.set.execute(world.admin, world.fasi.id, world.official_version.id)

    assert refused.value.code == "VERSAO_SUBSTITUIDA"


def test_two_marks_of_the_same_unit_end_with_one_row_one_create_and_one_update(world, engine):
    # Two tables of their own: only the lock of the unit makes the second mark wait.
    second = version_of_another_table(world, world.fasi, "Tabela Sintética B")
    third = version_of_another_table(world, world.fasi, "Tabela Sintética C")
    gate = Gate()
    first_factory = hooked_factory(
        engine, ("set_unit_default",), lambda _name: gate.hold()
    )
    first = Worker(
        lambda: SetUnitDefaultVersion(first_factory, world.audit).execute(
            world.admin, world.fasi.id, second.id
        )
    ).start()
    gate.wait_reached()  # the first holds the locks and has written, without committing
    other = Worker(
        lambda: SetUnitDefaultVersion(world.uow_factory, world.audit).execute(
            world.admin, world.fasi.id, third.id
        )
    ).start()
    wait_until_blocked(engine)

    gate.release()
    first.join()
    other.join()

    assert first.error is None and other.error is None
    assert mark_of(world, world.fasi) == third.id  # the last one wins
    with engine.connect() as conn:
        rows = conn.exec_driver_sql("SELECT count(*) FROM scoring_unit_defaults").scalar_one()
    assert rows == 1
    created, updated = events_of(world, world.fasi)
    assert (created.action, updated.action) == (AuditAction.CREATE, AuditAction.UPDATE)
    assert created.changes["version_id"]["after"] == str(second.id)
    assert updated.changes["version_id"] == {"before": str(second.id), "after": str(third.id)}


def test_marking_while_the_table_is_being_archived_ends_in_409_and_without_a_mark(world, engine):
    table_id = world.official_version.table_id
    gate = Gate()

    def archiving():
        with world.uow_factory() as uow:
            uow.scoring_tables.lock_table(table_id)
            uow.scoring_tables.set_table_archived(table_id, True)
            gate.hold()
            uow.commit()

    archive = Worker(archiving).start()
    gate.wait_reached()
    marking = Worker(
        lambda: SetUnitDefaultVersion(world.uow_factory, world.audit).execute(
            world.admin, world.fasi.id, world.official_version.id
        )
    ).start()
    wait_until_blocked(engine)

    gate.release()
    archive.join()
    marking.join()

    assert archive.error is None
    assert isinstance(marking.error, Conflict)
    assert marking.error.code == "TABELA_ARQUIVADA"
    assert mark_of(world, world.fasi) is None
    assert events_of(world, world.fasi) == []
