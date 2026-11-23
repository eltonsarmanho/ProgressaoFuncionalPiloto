"""GTAB-26, GTAB-27, GTAB-04: boundaries and lock races the first tests of the feature left
unpinned (verification of gestao-tabelas). Tables are synthetic.

- two deletions of the two versions of one table never leave it without a version (the table
  lock of DeleteScoringVersion);
- a clear that overlaps a mark audits the version it really removed (the unit lock of
  ClearUnitDefaultVersion);
- deleting a version that is not the latest does not reopen the previous one (A11);
- deleting the latest version reopens the previous one only if the deleted one closed it
  (ADM-05), which the CREATE event of the deleted version records (fix F1 of validation.md);
- creating a version while the latest one is deleted is not a deadlock (the table lock of
  CreateVersionFrom and ImportCriteriaCsv, fix F8).
"""

from datetime import date
from types import SimpleNamespace

import pytest

from app.application.use_cases import scoring_admin
from app.application.use_cases.scoring_admin import DeleteScoringVersion, ProtectedCatalog
from app.application.use_cases.scoring_defaults import (
    UNIT_DEFAULT_ENTITY,
    ClearUnitDefaultVersion,
    SetUnitDefaultVersion,
)
from app.domain.errors import Conflict
from tests.integration.scoring.conftest import OFFICIAL_TABLE
from tests.support.races import Gate, Worker, hooked_factory, wait_until_blocked

REFERENCE = "Res. 7.000/2026-CONSEPE"


@pytest.fixture
def uc(world):
    catalog = ProtectedCatalog(OFFICIAL_TABLE)
    return SimpleNamespace(
        delete=DeleteScoringVersion(world.uow_factory, world.audit, catalog),
        create_table=scoring_admin.CreateScoringTable(world.uow_factory, world.audit),
        create_version=scoring_admin.CreateVersionFrom(world.uow_factory, world.audit),
    )


def test_two_deletions_of_the_two_versions_of_a_table_never_leave_it_without_a_version(
    world, uc, engine
):
    table = uc.create_table.execute(
        world.admin, "Tabela Sintética Irmãs", [], date(2020, 1, 1), None, REFERENCE,
        base_version_id=world.official_version.id,
    )
    first = table.versions[0].version
    second = uc.create_version.execute(
        world.admin, table.table.id, first.id, date(2024, 1, 1), None, REFERENCE
    ).version
    gate = Gate()
    holding = hooked_factory(engine, ("count_criteria",), lambda _n: gate.hold())
    slow_delete = DeleteScoringVersion(holding, world.audit, ProtectedCatalog(OFFICIAL_TABLE))
    one = Worker(lambda: slow_delete.execute(world.admin, second.id)).start()
    gate.wait_reached()  # the latest is deleted and its locks are held, not committed
    other = Worker(lambda: uc.delete.execute(world.admin, first.id)).start()
    wait_until_blocked(engine)  # the second deletion must wait for the table lock

    gate.release()
    one.join()
    other.join()

    assert one.error is None
    assert isinstance(other.error, Conflict)
    assert other.error.code == "ULTIMA_VERSAO_DA_TABELA"
    with world.uow_factory() as uow:
        assert len(uow.scoring_tables.list_version_headers(table.table.id)) == 1


def test_clearing_while_another_mark_is_being_written_records_the_version_it_really_removed(
    world, engine
):
    third_table = scoring_admin.CreateScoringTable(world.uow_factory, world.audit).execute(
        world.admin, "Tabela Sintética Marcada B", [world.fasi.id], date(2020, 1, 1), None,
        REFERENCE, base_version_id=world.official_version.id,
    )
    other = third_table.versions[0].version
    SetUnitDefaultVersion(world.uow_factory, world.audit).execute(
        world.admin, world.fasi.id, world.official_version.id
    )
    gate = Gate()
    holding = hooked_factory(engine, ("set_unit_default",), lambda _n: gate.hold())
    setting = Worker(
        lambda: SetUnitDefaultVersion(holding, world.audit).execute(
            world.admin, world.fasi.id, other.id
        )
    ).start()
    gate.wait_reached()
    clearing = Worker(
        lambda: ClearUnitDefaultVersion(world.uow_factory, world.audit).execute(
            world.admin, world.fasi.id
        )
    ).start()
    wait_until_blocked(engine)

    gate.release()
    setting.join()
    clearing.join()

    assert setting.error is None and clearing.error is None
    with world.uow_factory() as uow:
        events = uow.audit.list_for(UNIT_DEFAULT_ENTITY, str(world.fasi.id))
        events = sorted(events, key=lambda e: e.id)
    assert events[-1].changes == {"version_id": {"before": str(other.id), "after": None}}


def test_deleting_a_middle_version_does_not_reopen_the_first_one(world, uc):
    table = uc.create_table.execute(
        world.admin, "Tabela Sintética Meio", [], date(2020, 1, 1), None, REFERENCE,
        base_version_id=world.official_version.id,
    )
    first = table.versions[0].version
    second = uc.create_version.execute(
        world.admin, table.table.id, first.id, date(2024, 1, 1), None, REFERENCE
    ).version
    uc.create_version.execute(
        world.admin, table.table.id, first.id, date(2026, 1, 1), None, REFERENCE
    )

    uc.delete.execute(world.admin, second.id)  # not the latest: A11 does not apply

    with world.uow_factory() as uow:
        assert uow.scoring_tables.get_version(first.id).valid_to == date(2023, 12, 31)


def test_deleting_the_latest_does_not_reopen_a_previous_version_the_admin_ended_himself(
    world, uc
):
    table = uc.create_table.execute(
        world.admin, "Tabela Sintética Encerrada", [], date(2020, 1, 1), date(2023, 12, 31),
        REFERENCE, base_version_id=world.official_version.id,
    )
    first = table.versions[0].version
    second = uc.create_version.execute(
        world.admin, table.table.id, first.id, date(2024, 1, 1), None, REFERENCE
    ).version  # nothing was open: the creation closed nothing

    uc.delete.execute(world.admin, second.id)

    with world.uow_factory() as uow:
        assert uow.scoring_tables.get_version(first.id).valid_to == date(2023, 12, 31)


def test_deleting_the_latest_does_not_reopen_an_adjacent_version_it_never_closed(world, uc):
    table = uc.create_table.execute(
        world.admin, "Tabela Sintética Vizinha", [], date(2020, 1, 1), None, REFERENCE,
        base_version_id=world.official_version.id,
    )
    first = table.versions[0].version
    middle = uc.create_version.execute(
        world.admin, table.table.id, first.id, date(2024, 1, 1), None, REFERENCE
    ).version  # closes the first on 2023-12-31
    latest = uc.create_version.execute(
        world.admin, table.table.id, first.id, date(2026, 1, 1), None, REFERENCE
    ).version  # closes the middle one on 2025-12-31
    uc.delete.execute(world.admin, middle.id)  # not the latest: the first stays closed
    inserted = uc.create_version.execute(
        world.admin, table.table.id, first.id, date(2024, 1, 1), date(2025, 12, 31), REFERENCE
    ).version  # ends the day before the latest starts, but the latest did not close it

    uc.delete.execute(world.admin, latest.id)

    with world.uow_factory() as uow:
        assert uow.scoring_tables.get_version(inserted.id).valid_to == date(2025, 12, 31)
        assert uow.scoring_tables.get_version(first.id).valid_to == date(2023, 12, 31)


def test_creating_a_version_while_the_latest_one_is_being_deleted_is_not_a_deadlock(
    world, uc, engine
):
    table = uc.create_table.execute(
        world.admin, "Tabela Sintética Corrida", [], date(2020, 1, 1), None, REFERENCE,
        base_version_id=world.official_version.id,
    )
    first = table.versions[0].version
    latest = uc.create_version.execute(
        world.admin, table.table.id, first.id, date(2024, 1, 1), None, REFERENCE
    ).version
    gate = Gate()
    holding = hooked_factory(engine, ("update_version",), lambda _n: gate.hold())
    slow_creation = scoring_admin.CreateVersionFrom(holding, world.audit)
    creating = Worker(
        lambda: slow_creation.execute(
            world.admin, table.table.id, first.id, date(2026, 1, 1), None, REFERENCE
        )
    ).start()
    gate.wait_reached()  # the open version is closed and its row is locked, not committed
    deleting = Worker(lambda: uc.delete.execute(world.admin, latest.id)).start()
    wait_until_blocked(engine)  # the deletion has to wait for the creation

    gate.release()
    creating.join()
    deleting.join()

    assert creating.error is None  # a deadlock would abort one of the two with 40P01
    assert deleting.error is None or isinstance(deleting.error, Conflict)
    with world.uow_factory() as uow:
        headers = uow.scoring_tables.list_version_headers(table.table.id)
    assert date(2026, 1, 1) in {v.valid_from for v in headers}

