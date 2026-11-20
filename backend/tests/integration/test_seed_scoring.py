"""OFI-01, OFI-08..OFI-12: idempotent seed of the official UFPA table and archiving of old ones."""

import uuid
from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import text

from app.domain.entities.career import Modality
from app.domain.entities.process import FunctionalProcess
from app.domain.entities.professor import Professor, Titration, WorkRegime
from app.domain.entities.scoring import (
    ScoringCriterion,
    ScoringGroup,
    ScoringMode,
    ScoringTableVersion,
    TableStatus,
)
from app.domain.entities.user import Role, User
from app.domain.errors import NotFound
from app.domain.repositories.ports import ScoringTableRecord
from app.infrastructure.database import seed
from app.infrastructure.database.seed import seed_reference_data, seed_scoring_tables
from tests.integration.test_seed import ADMIN_EMAIL, FakeHasher

OFFICIAL = "Tabela de Pontuação da UFPA"
LEGACY = ("Tabela de Pontuação do IFCH", "Tabela de Pontuação da FASI")
COUNTS = [2, 16, 9, 6, 5, 14, 11, 37]
MINIMUMS = {
    "structure": "Res. 4.644/2015-CONSEPE",
    "norm_reference": "Res. 4.644/2015-CONSEPE, art. 12",
    "by_current_class": {"A": 60, "B": 80, "C": 100, "D": 120},
}


@pytest.fixture
def units(uow_factory):
    seed_reference_data(uow_factory(), ADMIN_EMAIL, "first-password", FakeHasher())
    with uow_factory() as uow:
        return {u.acronym: u.id for u in uow.units.list()}


@pytest.fixture
def seeded(uow_factory, units):
    seed_scoring_tables(uow_factory())


def _counts(engine) -> dict[str, int]:
    tables = ("scoring_tables", "scoring_table_units", "scoring_table_versions", "scoring_groups",
              "scoring_criteria")  # fmt: skip
    with engine.connect() as conn:
        return {t: conn.execute(text(f"SELECT count(*) FROM {t}")).scalar_one() for t in tables}


def _by_table(uow_factory):
    with uow_factory() as uow:
        acronyms = {u.id: u.acronym for u in uow.units.list()}
        result = {}
        for table in uow.scoring_tables.list_tables():
            versions = uow.scoring_tables.list_versions(table.id)
            result[table.name] = (table, versions, {acronyms[i] for i in table.unit_ids})
    return result


def _legacy_version(name: str) -> ScoringTableVersion:
    criterion = ScoringCriterion(
        group_number=2, item_number=1, description="Item", unit_label="por aluno",
        mode=ScoringMode.POR_UNIDADE, unit_points=Decimal("5"),
    )  # fmt: skip
    return ScoringTableVersion(
        table_id=None, name="Versão antiga", valid_from=date(2022, 11, 23), valid_to=None,
        norm_reference=name, status=TableStatus.OFICIAL,
        groups=(ScoringGroup(number=2, name="Orientação", criteria=(criterion,)),),
    )  # fmt: skip


def _add_legacy_table(uow_factory, units, name: str, acronym: str) -> uuid.UUID:
    table = ScoringTableRecord(id=uuid.uuid4(), name=name, unit_ids=(units[acronym],))
    with uow_factory() as uow:
        uow.scoring_tables.add_table(table)
        uow.scoring_tables.add_version(replace(_legacy_version(name), table_id=table.id))
        uow.commit()
    return table.id


def _choose_version_in_a_process(uow_factory, units, table_id: uuid.UUID) -> uuid.UUID:
    with uow_factory() as uow:
        version = uow.scoring_tables.list_versions(table_id)[0]
        admin = User(uuid.uuid4(), "criador@ufpa.br", "Criador", Role.ADMIN, "x")
        uow.users.add(admin)
        professor = Professor(
            id=uuid.uuid4(), full_name="Docente", siape="1000001", titration=Titration.DOUTORADO,
            position="Professor do Magistério Superior",
            career_structure_id=uow.career_versions.structure_id("MAGISTERIO_SUPERIOR"),
            unit_id=units["FASI"], faculty="FASI", campus="Campus", work_regime=WorkRegime.DE,
        )  # fmt: skip
        uow.professors.add(professor)
        process = FunctionalProcess(
            id=uuid.uuid4(), professor_id=professor.id, unit_id=units["FASI"],
            modality=Modality.PROMOCAO, current_class="C", current_denomination="Adjunto",
            current_level=4, target_class="D", target_denomination="Associado", target_level=1,
            start_date=date(2022, 11, 23), end_date=date(2024, 11, 23),
            opening_date=date(2025, 3, 10), created_by=admin.id,
        )  # fmt: skip
        uow.processes.add(process)
        uow.processes.set_scoring_table_version(process.id, version.id)
        uow.commit()
        return version.id


def test_empty_database_gets_only_the_official_table_for_fasi_and_ifch(uow_factory, seeded):
    tables = _by_table(uow_factory)

    assert list(tables) == [OFFICIAL]
    table, versions, acronyms = tables[OFFICIAL]
    assert acronyms == {"FASI", "IFCH"}
    assert table.archived is False
    assert [v.status.value for v in versions] == ["OFICIAL"]


def test_official_version_metadata_and_structure(uow_factory, seeded):
    _, versions, _ = _by_table(uow_factory)[OFFICIAL]
    version = versions[0]

    assert version.valid_from == date(2015, 3, 24)
    assert version.valid_to is None
    assert version.norm_reference == (
        "Tabela oficial de pontuação para progressão docente da UFPA "
        "(planilha fornecida pelo usuário em 2026-11-17)"
    )
    assert [g.number for g in version.groups] == list(range(1, 9))
    assert [len(g.criteria) for g in version.groups] == COUNTS
    assert version.get_group(1).counts_in_total is False


def test_minimums_are_stored_with_the_norm_reference(uow_factory, seeded):
    _, versions, _ = _by_table(uow_factory)[OFFICIAL]
    assert versions[0].minimums == MINIMUMS


def test_minimum_hours_and_unit_values_survive_the_database(uow_factory, seeded):
    _, versions, _ = _by_table(uow_factory)[OFFICIAL]
    version = versions[0]

    assert [version.get_criterion(4, i).min_hours for i in (3, 4, 5)] == [Decimal("20")] * 3
    assert version.get_criterion(4, 6).min_hours is None
    assert version.get_criterion(2, 10).unit_points == Decimal("10")
    assert version.get_criterion(7, 11).hours_per_block == Decimal("30")
    assert version.get_criterion(8, 37).unit_points == Decimal("0")


def test_seed_twice_does_not_duplicate_anything(engine, uow_factory, seeded):
    first = _counts(engine)
    seed_scoring_tables(uow_factory())

    assert first == {
        "scoring_tables": 1,
        "scoring_table_units": 2,
        "scoring_table_versions": 1,
        "scoring_groups": 8,
        "scoring_criteria": sum(COUNTS),
    }
    assert _counts(engine) == first


def test_the_old_ifch_and_fasi_seeds_are_gone(engine, uow_factory, seeded):
    names = set(_by_table(uow_factory))
    assert not names & set(LEGACY)


def test_unused_legacy_tables_are_archived_and_lose_their_units(uow_factory, units, engine):
    ids = {
        name: _add_legacy_table(uow_factory, units, name, acronym)
        for name, acronym in zip(LEGACY, ("IFCH", "FASI"), strict=True)
    }

    seed_scoring_tables(uow_factory())

    tables = _by_table(uow_factory)
    for name in LEGACY:
        table, versions, acronyms = tables[name]
        assert table.id == ids[name]
        assert table.archived is True
        assert acronyms == set()
        assert len(versions) == 1  # nothing deleted
    assert tables[OFFICIAL][0].archived is False
    assert tables[OFFICIAL][2] == {"FASI", "IFCH"}


def test_unit_listing_returns_only_the_official_version_after_archiving(uow_factory, units):
    for name, acronym in zip(LEGACY, ("IFCH", "FASI"), strict=True):
        _add_legacy_table(uow_factory, units, name, acronym)

    seed_scoring_tables(uow_factory())

    with uow_factory() as uow:
        for acronym in ("FASI", "IFCH"):
            versions = uow.scoring_tables.list_versions_for_unit(units[acronym])
            assert [v.norm_reference.split(" ")[0] for v in versions] == ["Tabela"]
            assert [v.status.value for v in versions] == ["OFICIAL"]
            assert all(v.valid_from == date(2015, 3, 24) for v in versions)


def test_legacy_table_with_a_version_chosen_by_a_process_is_left_untouched(uow_factory, units):
    used = _add_legacy_table(uow_factory, units, LEGACY[1], "FASI")
    unused = _add_legacy_table(uow_factory, units, LEGACY[0], "IFCH")
    version_id = _choose_version_in_a_process(uow_factory, units, used)

    seed_scoring_tables(uow_factory())

    tables = _by_table(uow_factory)
    kept, kept_versions, kept_units = tables[LEGACY[1]]
    assert (kept.id, kept.archived, kept_units) == (used, False, {"FASI"})
    assert [v.id for v in kept_versions] == [version_id]
    assert tables[LEGACY[0]][0].id == unused
    assert tables[LEGACY[0]][0].archived is True


def test_rerun_with_archived_old_tables_changes_nothing(engine, uow_factory, units):
    for name, acronym in zip(LEGACY, ("IFCH", "FASI"), strict=True):
        _add_legacy_table(uow_factory, units, name, acronym)
    seed_scoring_tables(uow_factory())
    first = _counts(engine)
    before = {n: (t.archived, tuple(t.unit_ids)) for n, (t, _, _) in _by_table(uow_factory).items()}

    seed_scoring_tables(uow_factory())

    assert _counts(engine) == first
    after = {n: (t.archived, tuple(t.unit_ids)) for n, (t, _, _) in _by_table(uow_factory).items()}
    assert after == before


def test_seed_requires_the_academic_units(uow_factory):
    with pytest.raises(LookupError, match="FASI"):
        seed_scoring_tables(uow_factory())


def test_main_entrypoint_seeds_the_official_table(migrated_url, engine, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", migrated_url)
    monkeypatch.setenv("ADMIN_EMAIL", ADMIN_EMAIL)
    monkeypatch.setenv("ADMIN_PASSWORD", "admin-password-123")

    seed.main()

    assert _counts(engine)["scoring_tables"] == 1


def test_archiving_an_unknown_table_is_not_found(uow_factory):
    with uow_factory() as uow, pytest.raises(NotFound):
        uow.scoring_tables.set_table_archived(uuid.uuid4(), True)
