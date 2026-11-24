"""OFI-12: min_hours survives the round trip, edits, table duplication and new versions."""

import uuid
from datetime import date
from decimal import Decimal

import pytest

from app.domain.entities.scoring import (
    ScoringCriterion,
    ScoringGroup,
    ScoringMode,
    ScoringTableVersion,
    TableStatus,
)
from app.domain.repositories.ports import ScoringTableRecord

D = Decimal


def course(item, min_hours) -> ScoringCriterion:
    return ScoringCriterion(
        4, item, f"IV.{item}", "curso", ScoringMode.POR_UNIDADE,
        unit_points=D("5"), min_hours=min_hours,
    )  # fmt: skip


@pytest.fixture
def stored(world):
    """A table of the FASI unit whose group IV has criteria with and without min_hours."""
    table = ScoringTableRecord(uuid.uuid4(), "Tabela com carga mínima", unit_ids=(world.fasi.id,))
    version = ScoringTableVersion(
        table_id=table.id,
        name="Versão 1",
        valid_from=date(2015, 3, 24),
        valid_to=None,
        norm_reference="Tabela de teste",
        status=TableStatus.OFICIAL,
        groups=(
            ScoringGroup(
                4, "Grupo IV",
                criteria=(course(3, D("20")), course(4, D("19.5")), course(6, None)),
            ),
        ),
        id=uuid.uuid4(),
    )  # fmt: skip
    with world.uow_factory() as uow:
        uow.scoring_tables.add_table(table)
        uow.scoring_tables.add_version(version)
        uow.commit()
    world.table, world.version = table, version
    return world


def minimums(version) -> dict[int, Decimal | None]:
    return {c.item_number: c.min_hours for c in version.get_group(4).criteria}


def test_criterion_with_and_without_min_hours_round_trip(stored):
    with stored.uow_factory() as uow:
        loaded = uow.scoring_tables.get_version(stored.version.id)

    assert minimums(loaded) == {3: D("20"), 4: D("19.5"), 6: None}
    assert loaded == stored.version


def test_min_hours_is_read_through_the_listings_too(stored):
    with stored.uow_factory() as uow:
        by_table = uow.scoring_tables.list_versions(stored.table.id)
        by_unit = [
            v for v in uow.scoring_tables.list_versions_for_unit(stored.fasi.id)
            if v.id == stored.version.id
        ]  # fmt: skip

    assert minimums(by_table[0])[3] == D("20")
    assert minimums(by_unit[0])[3] == D("20")


def test_update_criterion_sets_and_clears_min_hours(stored):
    version_id = stored.version.id
    with stored.uow_factory() as uow:
        uow.scoring_tables.update_criterion(version_id, course(6, D("30")))
        uow.scoring_tables.update_criterion(version_id, course(3, None))
        uow.commit()
    with stored.uow_factory() as uow:
        loaded = uow.scoring_tables.get_version(version_id)

    assert minimums(loaded) == {3: None, 4: D("19.5"), 6: D("30")}


def test_duplicating_a_table_copies_min_hours(stored, admin_uc):
    created = admin_uc.duplicate.execute(
        stored.admin, stored.table.id, "Cópia com carga mínima", [stored.fasi.id]
    )

    with stored.uow_factory() as uow:
        [copy] = uow.scoring_tables.list_versions(created.table.id)
    assert minimums(copy) == {3: D("20"), 4: D("19.5"), 6: None}


def test_a_new_version_copies_min_hours_from_its_source(stored, admin_uc):
    created = admin_uc.create_version.execute(
        stored.admin, stored.table.id, stored.version.id,
        date(2027, 1, 1), None, "Res. de teste",
    )  # fmt: skip

    with stored.uow_factory() as uow:
        loaded = uow.scoring_tables.get_version(created.version.id)
    assert loaded.id != stored.version.id
    assert minimums(loaded) == {3: D("20"), 4: D("19.5"), 6: None}
