"""TAB-03, TAB-04, TAB-06, SEL-01, VERIF-10: idempotent scoring tables seed."""

from decimal import Decimal

import pytest
from sqlalchemy import text

from app.infrastructure.database import seed
from app.infrastructure.database.seed import seed_reference_data, seed_scoring_tables
from tests.integration.test_seed import ADMIN_EMAIL, FakeHasher

COUNTS = [3, 16, 12, 7, 6, 14, 11, 66]
MINIMUMS = {
    "structure": "Res. 4.644/2015-CONSEPE",
    "norm_reference": "Res. 4.644/2015-CONSEPE, art. 12",
    "by_current_class": {"A": 60, "B": 80, "C": 100, "D": 120},
}


@pytest.fixture
def seeded(uow_factory):
    seed_reference_data(uow_factory(), ADMIN_EMAIL, "first-password", FakeHasher())
    seed_scoring_tables(uow_factory())


def _counts(engine) -> dict[str, int]:
    tables = ("scoring_tables", "scoring_table_units", "scoring_table_versions", "scoring_groups",
              "scoring_criteria")  # fmt: skip
    with engine.connect() as conn:
        return {t: conn.execute(text(f"SELECT count(*) FROM {t}")).scalar_one() for t in tables}


def _by_table(uow_factory):
    with uow_factory() as uow:
        units = {u.id: u.acronym for u in uow.units.list()}
        result = {}
        for table in uow.scoring_tables.list_tables():
            versions = uow.scoring_tables.list_versions(table.id)
            result[table.name] = (table, versions, {units[i] for i in table.unit_ids})
    return result


def test_seed_twice_does_not_duplicate_anything(engine, uow_factory, seeded):
    first = _counts(engine)
    seed_scoring_tables(uow_factory())

    assert first == {
        "scoring_tables": 2,
        "scoring_table_units": 2,
        "scoring_table_versions": 2,
        "scoring_groups": 16,
        "scoring_criteria": 270,
    }
    assert _counts(engine) == first


def test_each_table_has_the_annex_structure(uow_factory, seeded):
    for _, versions, _ in _by_table(uow_factory).values():
        assert len(versions) == 1
        assert [len(g.criteria) for g in versions[0].groups] == COUNTS
        assert [g.number for g in versions[0].groups] == list(range(1, 9))


def test_ifch_is_official_and_group_one_does_not_count(uow_factory, seeded):
    table, versions, units = _by_table(uow_factory)["Tabela de Pontuação do IFCH"]
    version = versions[0]
    assert units == {"IFCH"}
    assert version.status.value == "OFICIAL"
    assert version.get_group(1).counts_in_total is False
    assert version.get_criterion(2, 2).unit_points == Decimal("30")
    assert version.get_criterion(1, 3).max_points == Decimal("10")


def test_fasi_is_pending_and_group_one_counts(uow_factory, seeded):
    table, versions, units = _by_table(uow_factory)["Tabela de Pontuação da FASI"]
    version = versions[0]
    assert units == {"FASI"}
    assert version.status.value == "PENDENTE_VALIDACAO"
    assert version.get_group(1).counts_in_total is True
    assert version.get_criterion(1, 1).weeks_per_semester == 17
    assert version.get_criterion(1, 2).prep_ratio == Decimal("2")
    assert version.get_criterion(2, 12).unit_points == Decimal("10")
    assert version.get_criterion(8, 38).review_note


def test_minimums_are_stored_with_the_norm_reference(uow_factory, seeded):
    for _, versions, _ in _by_table(uow_factory).values():
        assert versions[0].minimums == MINIMUMS


def test_each_unit_gets_its_own_table_version(uow_factory, seeded):
    with uow_factory() as uow:
        units = {u.acronym: u.id for u in uow.units.list()}
        ifch = uow.scoring_tables.list_versions_for_unit(units["IFCH"])
        fasi = uow.scoring_tables.list_versions_for_unit(units["FASI"])
    assert [v.norm_reference.split(" ")[0] for v in ifch] == ["Tabela"]
    assert [v.status.value for v in ifch] == ["OFICIAL"]
    assert [v.status.value for v in fasi] == ["PENDENTE_VALIDACAO"]


def test_main_entrypoint_seeds_the_scoring_tables(migrated_url, engine, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", migrated_url)
    monkeypatch.setenv("ADMIN_EMAIL", ADMIN_EMAIL)
    monkeypatch.setenv("ADMIN_PASSWORD", "admin-password-123")

    seed.main()

    assert _counts(engine)["scoring_tables"] == 2
