"""GTAB-23, GTAB-25, GTAB-31: archive and unarchive a scoring table, with the in-use guard."""

import uuid
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.application.use_cases.scoring import ActivityData
from app.application.use_cases.scoring_admin import TABLE_ENTITY, ArchiveScoringTable
from app.application.use_cases.scoring_defaults import SetUnitDefaultVersion
from app.domain.entities.audit import AuditAction
from app.domain.errors import Conflict, Forbidden, NotFound
from tests.support.races import Gate, Worker, hooked_factory, wait_until_blocked


@pytest.fixture
def uc(world):
    return SimpleNamespace(
        archive=ArchiveScoringTable(world.uow_factory, world.audit),
        mark=SetUnitDefaultVersion(world.uow_factory, world.audit),
    )


def table_id(world):
    return world.official_version.table_id


def is_archived(world, table=None):
    with world.uow_factory() as uow:
        return uow.scoring_tables.get_table(table or table_id(world)).archived


def events(world, table=None):
    with world.uow_factory() as uow:
        return list(uow.audit.list_for(TABLE_ENTITY, str(table or table_id(world))))


def mark_of(world, unit):
    with world.uow_factory() as uow:
        found = uow.scoring_tables.get_unit_default(unit.id)
    return found.version_id if found else None


def test_archiving_writes_an_archive_event_with_the_user_and_the_change(world, uc):
    view = uc.archive.execute(world.admin, table_id(world), True)

    assert view.table.archived is True
    assert view.table.id == table_id(world)
    assert is_archived(world) is True
    (event,) = events(world)
    assert event.action is AuditAction.ARCHIVE
    assert event.user_id == world.admin.id
    assert event.entity == "scoring_table"
    assert event.entity_id == str(table_id(world))
    assert event.changes == {"archived": {"before": False, "after": True}}


def test_unarchiving_writes_an_update_event_and_the_table_is_back(world, uc):
    uc.archive.execute(world.admin, table_id(world), True)

    view = uc.archive.execute(world.admin, table_id(world), False)

    assert view.table.archived is False
    assert is_archived(world) is False
    archived, unarchived = events(world)
    assert (archived.action, unarchived.action) == (AuditAction.ARCHIVE, AuditAction.UPDATE)
    assert unarchived.user_id == world.admin.id
    assert unarchived.changes == {"archived": {"before": True, "after": False}}


def test_repeating_either_direction_writes_no_event(world, uc):
    uc.archive.execute(world.admin, table_id(world), False)  # already not archived
    assert events(world) == []

    uc.archive.execute(world.admin, table_id(world), True)
    uc.archive.execute(world.admin, table_id(world), True)  # already archived

    assert len(events(world)) == 1
    assert is_archived(world) is True


def test_the_view_lists_the_versions_of_the_table(world, uc):
    view = uc.archive.execute(world.admin, table_id(world), True)

    assert [v.version.id for v in view.versions] == [world.official_version.id]


def test_a_table_with_a_version_in_use_is_refused_with_409_and_the_acronyms(world, uc):
    uc.mark.execute(world.admin, world.ifch.id, world.official_version.id)
    uc.mark.execute(world.admin, world.fasi.id, world.official_version.id)

    with pytest.raises(Conflict) as refused:
        uc.archive.execute(world.admin, table_id(world), True)

    assert refused.value.code == "TABELA_COM_VERSAO_EM_USO"
    assert str(refused.value) == (
        "A tabela tem versão em uso das unidades FASI, IFCH; marque outra tabela ou "
        "desmarque a versão antes de arquivar"
    )
    assert is_archived(world) is False
    assert events(world) == []


def test_a_mark_in_another_table_does_not_block_archiving_this_one(world, uc):
    other_table = world.other_version.table_id
    with world.uow_factory() as uow:
        uow.scoring_tables.set_table_units(other_table, (world.fasi.id,))
        uow.commit()
    uc.mark.execute(world.admin, world.fasi.id, world.other_version.id)

    uc.archive.execute(world.admin, table_id(world), True)

    assert is_archived(world) is True
    assert mark_of(world, world.fasi) == world.other_version.id


def test_unarchiving_is_allowed_and_creates_no_mark(world, uc):
    uc.archive.execute(world.admin, table_id(world), True)

    uc.archive.execute(world.admin, table_id(world), False)

    assert mark_of(world, world.fasi) is None
    assert mark_of(world, world.ifch) is None


def test_a_non_admin_gets_403_and_nothing_changes(world, uc):
    for actor in (world.docente, world.secretaria):
        with pytest.raises(Forbidden):
            uc.archive.execute(actor, table_id(world), True)

    assert is_archived(world) is False
    assert events(world) == []


def test_an_unknown_table_is_404(world, uc):
    with pytest.raises(NotFound):
        uc.archive.execute(world.admin, uuid.uuid4(), True)


def test_an_archived_table_is_still_read_and_still_scores_a_process_that_uses_it(
    official_chosen, uc
):
    world = official_chosen
    world.create.execute(
        world.admin,
        world.process.id,
        ActivityData(
            title="Orientação",
            group_number=2,
            item_number=7,
            quantity=Decimal("4"),
            evidence_note="Declaração",
            event_date=world.process.start_date,
        ),
    )
    before = world.calc.execute(world.admin, world.process.id).result.total

    uc.archive.execute(world.admin, table_id(world), True)

    score = world.calc.execute(world.admin, world.process.id)
    assert before == Decimal("20")
    assert score.result.total == before
    assert score.chosen.version.id == world.official_version.id
    with world.uow_factory() as uow:
        assert uow.scoring_tables.get_table(table_id(world)).archived is True
        assert uow.scoring_tables.get_version(world.official_version.id) is not None


def test_archiving_while_a_version_is_being_marked_ends_with_the_archiving_refused(world, engine):
    gate = Gate()
    marking_factory = hooked_factory(engine, ("set_unit_default",), lambda _name: gate.hold())
    marking = Worker(
        lambda: SetUnitDefaultVersion(marking_factory, world.audit).execute(
            world.admin, world.fasi.id, world.official_version.id
        )
    ).start()
    gate.wait_reached()  # the mark is written and holds the lock of the table, not committed
    archiving = Worker(
        lambda: ArchiveScoringTable(world.uow_factory, world.audit).execute(
            world.admin, table_id(world), True
        )
    ).start()
    wait_until_blocked(engine)

    gate.release()
    marking.join()
    archiving.join()

    assert marking.error is None
    assert isinstance(archiving.error, Conflict)
    assert archiving.error.code == "TABELA_COM_VERSAO_EM_USO"
    assert mark_of(world, world.fasi) == world.official_version.id
    assert is_archived(world) is False


def test_marking_while_the_table_is_being_archived_ends_with_the_mark_refused(world, engine):
    gate = Gate()
    archiving_factory = hooked_factory(engine, ("set_table_archived",), lambda _name: gate.hold())
    archiving = Worker(
        lambda: ArchiveScoringTable(archiving_factory, world.audit).execute(
            world.admin, table_id(world), True
        )
    ).start()
    gate.wait_reached()  # the table is archived and locked, not committed
    marking = Worker(
        lambda: SetUnitDefaultVersion(world.uow_factory, world.audit).execute(
            world.admin, world.fasi.id, world.official_version.id
        )
    ).start()
    wait_until_blocked(engine)

    gate.release()
    archiving.join()
    marking.join()

    assert archiving.error is None
    assert isinstance(marking.error, Conflict)
    assert marking.error.code == "TABELA_ARQUIVADA"
    assert is_archived(world) is True
    assert mark_of(world, world.fasi) is None
