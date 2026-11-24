"""NLINK-01, NLINK-02: the norm code of a scoring table version, on real PostgreSQL."""

import uuid
from dataclasses import replace

from app.domain.repositories.ports import ScoringTableRecord
from app.infrastructure.database.seed import seed_reference_data, seed_scoring_tables
from tests.integration.test_scoring_repositories import (  # noqa: F401  (fixture and helper)
    base,
    make_version,
)
from tests.integration.test_seed import ADMIN_EMAIL, FakeHasher


def _store(uow_factory, base, **changes):  # noqa: F811
    table = ScoringTableRecord(uuid.uuid4(), "Tabela sintética", unit_ids=(base["unit"].id,))
    version = replace(make_version(table.id), **changes)
    with uow_factory() as uow:
        uow.scoring_tables.add_table(table)
        uow.scoring_tables.add_version(version)
        uow.commit()
    return table, version


def test_norm_code_makes_a_round_trip_through_add_and_get(uow_factory, base):  # noqa: F811
    table, version = _store(uow_factory, base, norm_code="NORMA-SINTETICA")

    with uow_factory() as uow:
        stored = uow.scoring_tables.get_version(version.id)
        listed = uow.scoring_tables.list_versions(table.id)
        for_unit = uow.scoring_tables.list_versions_for_unit(base["unit"].id)

    assert stored.norm_code == "NORMA-SINTETICA"
    assert [v.norm_code for v in listed] == ["NORMA-SINTETICA"]
    assert [v.norm_code for v in for_unit] == ["NORMA-SINTETICA"]


def test_a_version_without_a_norm_code_reads_none(uow_factory, base):  # noqa: F811
    _table, version = _store(uow_factory, base)

    with uow_factory() as uow:
        assert uow.scoring_tables.get_version(version.id).norm_code is None


def test_update_version_saves_the_norm_code_it_receives(uow_factory, base):  # noqa: F811
    _table, version = _store(uow_factory, base, norm_code="NORMA-A")

    with uow_factory() as uow:
        stored = uow.scoring_tables.get_version(version.id)
        uow.scoring_tables.update_version(replace(stored, notes="nota nova"))
        uow.commit()
    with uow_factory() as uow:
        kept = uow.scoring_tables.get_version(version.id)
        uow.scoring_tables.update_version(replace(kept, norm_code="NORMA-B"))
        uow.commit()
    with uow_factory() as uow:
        changed = uow.scoring_tables.get_version(version.id)

    assert (kept.norm_code, kept.notes) == ("NORMA-A", "nota nova")
    assert changed.norm_code == "NORMA-B"


def test_the_version_seeded_in_an_empty_database_carries_the_official_table_code(uow_factory):
    seed_reference_data(uow_factory(), ADMIN_EMAIL, "first-password", FakeHasher())
    seed_scoring_tables(uow_factory())

    with uow_factory() as uow:
        (table,) = uow.scoring_tables.list_tables()
        versions = uow.scoring_tables.list_versions(table.id)

    assert [v.norm_code for v in versions] == ["TABELA-OFICIAL-UFPA"]
