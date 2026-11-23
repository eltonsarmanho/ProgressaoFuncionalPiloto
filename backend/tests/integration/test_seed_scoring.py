"""OFI-01, OFI-08..OFI-12: idempotent seed of the official UFPA table and archiving of old ones."""

import json
import uuid
from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import text

from app.application.services.audit_service import AuditService
from app.application.use_cases.scoring_admin import ArchiveScoringTable, SetTableUnits
from app.application.use_cases.scoring_defaults import ClearUnitDefaultVersion
from app.domain.entities.audit import AuditAction
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
from app.infrastructure.clock import SystemClock
from app.infrastructure.database import seed
from app.infrastructure.database.seed import (
    seed_reference_data,
    seed_scoring_tables,
    seed_unit_defaults,
)
from tests.integration.test_seed import ADMIN_EMAIL, FakeHasher
from tests.support.scoring_variants import add_legacy_ufpa_version

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


def _choose_in_a_draft_process(uow_factory, units, version_id: uuid.UUID) -> uuid.UUID:
    """A draft process of FASI that chose the given version; returns the process id."""
    with uow_factory() as uow:
        admin = User(uuid.uuid4(), "criador2@ufpa.br", "Criador", Role.ADMIN, "x")
        uow.users.add(admin)
        professor = Professor(
            id=uuid.uuid4(), full_name="Docente", siape="1000002", titration=Titration.DOUTORADO,
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
        uow.processes.set_scoring_table_version(process.id, version_id)
        uow.commit()
        return process.id


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

    assert version.name == "Tabela oficial de pontuação UFPA, Grupo I no total"
    assert version.valid_from == date(2015, 3, 24)
    assert version.valid_to is None
    assert version.norm_reference == (
        "Tabela oficial de pontuação para progressão docente da UFPA "
        "(planilha fornecida em 2026-11-17), com o Grupo I somado ao total a 1 ponto por hora "
        "de PIT por decisão do usuário em 2026-11-19"
    )
    assert [g.number for g in version.groups] == list(range(1, 9))
    assert [len(g.criteria) for g in version.groups] == COUNTS
    # GI-07: group I counts in the total in the seeded version (was False).
    assert version.get_group(1).counts_in_total is True
    assert version.get_criterion(6, 14).unit_points == Decimal("3")  # GI-12
    assert version.superseded_by_id is None


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


def _seeded_json() -> dict:
    return json.loads((seed.SEED_DATA / seed.OFFICIAL_TABLE_SEED).read_text(encoding="utf-8"))


def test_a_database_with_the_previous_version_gets_the_new_one_beside_it_untouched(
    engine, uow_factory, units
):
    """GI-07: the seed inserts the new version next to the previous one (same table, same name
    of table) and neither changes nor marks it; the marking is the next step (AdoptSuperseding)."""
    data = _seeded_json()
    table = ScoringTableRecord(
        id=uuid.uuid4(), name=data["table_name"], unit_ids=(units["FASI"], units["IFCH"])
    )
    template = seed._scoring_version(data, table.id)
    with uow_factory() as uow:
        uow.scoring_tables.add_table(table)
        legacy = add_legacy_ufpa_version(uow, template)
        uow.commit()
    with uow_factory() as uow:
        before = uow.scoring_tables.get_version(legacy.id)

    seed_scoring_tables(uow_factory())

    _, versions, _ = _by_table(uow_factory)[OFFICIAL]
    assert sorted(v.name for v in versions) == [
        "Tabela oficial de pontuação UFPA",
        "Tabela oficial de pontuação UFPA, Grupo I no total",
    ]
    kept = next(v for v in versions if v.id == legacy.id)
    assert kept == before
    assert kept.get_group(1).counts_in_total is False
    assert kept.get_criterion(6, 14).unit_points == Decimal("6")
    new = next(v for v in versions if v.id != legacy.id)
    assert new.get_group(1).counts_in_total is True
    assert new.get_criterion(6, 14).unit_points == Decimal("3")
    assert _counts(engine)["scoring_tables"] == 1
    again = _counts(engine)
    seed_scoring_tables(uow_factory())
    assert _counts(engine) == again  # idempotent with the previous version present


def _process_events(engine, process_id) -> list:
    with engine.connect() as conn:
        return conn.execute(
            text(
                "SELECT user_id, changes, justification FROM audit_logs "
                "WHERE entity = 'process' AND entity_id = :i ORDER BY id"
            ),
            {"i": str(process_id)},
        ).all()


def test_seeding_over_the_previous_version_marks_it_and_moves_the_draft_process_once(
    engine, uow_factory, units
):
    """GI-07, GI-10: the seed hands the process of the previous version to the new one, with
    one audit event, and a second start (the entrypoint runs the seed on every start) does not."""
    data = _seeded_json()
    table = ScoringTableRecord(
        id=uuid.uuid4(), name=data["table_name"], unit_ids=(units["FASI"], units["IFCH"])
    )
    template = seed._scoring_version(data, table.id)
    with uow_factory() as uow:
        uow.scoring_tables.add_table(table)
        legacy = add_legacy_ufpa_version(uow, template)
        uow.commit()
    process_id = _choose_in_a_draft_process(uow_factory, units, legacy.id)

    seed_scoring_tables(uow_factory())

    with uow_factory() as uow:
        versions = {v.name: v for v in uow.scoring_tables.list_versions(table.id)}
        chosen = uow.processes.get(process_id).scoring_table_version_id
    new = versions[data["version_name"]]
    assert versions[data["supersedes"]].superseded_by_id == new.id
    assert new.superseded_by_id is None
    assert chosen == new.id
    [event] = _process_events(engine, process_id)
    assert event.user_id is None
    assert event.justification == "AD-023: Grupo I no total"
    assert event.changes == {
        "scoring_table_version_id": {"before": str(legacy.id), "after": str(new.id)}
    }

    seed_scoring_tables(uow_factory())  # the second start

    assert len(_process_events(engine, process_id)) == 1
    with uow_factory() as uow:
        assert uow.processes.get(process_id).scoring_table_version_id == new.id


def test_the_legacy_helper_recreates_the_previous_rules_next_to_the_seeded_version(
    uow_factory, seeded
):
    _, versions, _ = _by_table(uow_factory)[OFFICIAL]
    official = versions[0]

    with uow_factory() as uow:
        legacy = add_legacy_ufpa_version(uow, official)
        uow.commit()

    with uow_factory() as uow:
        loaded = uow.scoring_tables.get_version(legacy.id)
    assert loaded.table_id == official.table_id
    assert loaded.name == "Tabela oficial de pontuação UFPA"
    assert loaded.get_group(1).counts_in_total is False
    assert loaded.get_criterion(6, 14).unit_points == Decimal("6")
    assert loaded.superseded_by_id is None
    assert [g.counts_in_total for g in loaded.groups[1:]] == [True] * 7
    assert [len(g.criteria) for g in loaded.groups] == COUNTS


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
    with engine.connect() as conn:
        marks = conn.execute(
            text(
                "SELECT u.acronym, v.name FROM scoring_unit_defaults d "
                "JOIN academic_units u ON u.id = d.unit_id "
                "JOIN scoring_table_versions v ON v.id = d.version_id"
            )
        ).all()
    assert sorted(marks) == [
        ("FASI", seed._official_table_data()["version_name"]),
        ("IFCH", seed._official_table_data()["version_name"]),
    ]


def test_archiving_an_unknown_table_is_not_found(uow_factory):
    with uow_factory() as uow, pytest.raises(NotFound):
        uow.scoring_tables.set_table_archived(uuid.uuid4(), True)


# --- GTAB-09: the first mark of the version in use, once per unit -------------------------------

UNIT_DEFAULT = "unit_scoring_default"


def _marks(uow_factory) -> dict[str, uuid.UUID]:
    with uow_factory() as uow:
        acronyms = {u.id: u.acronym for u in uow.units.list()}
        return {
            acronyms[d.unit_id]: d.version_id for d in uow.scoring_tables.list_unit_defaults()
        }


def _mark_events(uow_factory, unit_id):
    with uow_factory() as uow:
        return list(uow.audit.list_for(UNIT_DEFAULT, str(unit_id)))


def _official_version_id(uow_factory):
    name = seed._official_table_data()["version_name"]
    with uow_factory() as uow:
        for table in uow.scoring_tables.list_tables():
            for version in uow.scoring_tables.list_versions(table.id):
                if version.name == name:
                    return version.id
    raise AssertionError("official version not seeded")


def test_the_seeded_tables_alone_leave_the_units_without_a_mark(uow_factory, units, seeded):
    assert _marks(uow_factory) == {}


def test_the_first_run_marks_fasi_and_ifch_with_the_official_version_and_two_system_events(
    uow_factory, units, seeded
):
    seed_unit_defaults(uow_factory())

    official = _official_version_id(uow_factory)
    assert _marks(uow_factory) == {"FASI": official, "IFCH": official}
    for acronym in ("FASI", "IFCH"):
        [event] = _mark_events(uow_factory, units[acronym])
        assert event.user_id is None
        assert event.action is AuditAction.CREATE
        assert event.entity == UNIT_DEFAULT
        assert event.changes == {"version_id": {"before": None, "after": str(official)}}


def test_the_second_run_writes_no_event_and_changes_no_row(uow_factory, engine, units, seeded):
    seed_unit_defaults(uow_factory())
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT * FROM scoring_unit_defaults ORDER BY unit_id")).all()
    events = {a: _mark_events(uow_factory, units[a]) for a in ("FASI", "IFCH")}

    seed_unit_defaults(uow_factory())

    with engine.connect() as conn:
        after = conn.execute(text("SELECT * FROM scoring_unit_defaults ORDER BY unit_id")).all()
    assert after == rows
    assert {a: _mark_events(uow_factory, units[a]) for a in ("FASI", "IFCH")} == events


def test_a_unit_that_the_admin_cleared_is_not_marked_again(uow_factory, units, seeded):
    seed_unit_defaults(uow_factory())
    admin = User(uuid.uuid4(), "adm@ufpa.br", "Adm", Role.ADMIN, "x")
    with uow_factory() as uow:
        uow.users.add(admin)
        uow.commit()
    ClearUnitDefaultVersion(uow_factory, AuditService(SystemClock())).execute(admin, units["FASI"])

    seed_unit_defaults(uow_factory())

    assert set(_marks(uow_factory)) == {"IFCH"}
    assert [e.action for e in _mark_events(uow_factory, units["FASI"])] == [
        AuditAction.CREATE,
        AuditAction.DELETE,
    ]


def test_a_unit_that_lost_its_mark_by_supersession_is_not_marked_again(uow_factory, units, seeded):
    seed_unit_defaults(uow_factory())
    with uow_factory() as uow:  # what AdoptSupersedingVersion does: a system DELETE event
        uow.scoring_tables.clear_unit_default(units["FASI"])
        AuditService(SystemClock()).record(
            uow, None, UNIT_DEFAULT, units["FASI"], AuditAction.DELETE,
            {"version_id": uuid.uuid4()}, {"version_id": None},
        )  # fmt: skip
        uow.commit()

    seed_unit_defaults(uow_factory())

    assert set(_marks(uow_factory)) == {"IFCH"}


def test_a_unit_without_the_official_table_associated_is_not_marked(uow_factory, units, seeded):
    with uow_factory() as uow:
        table = next(t for t in uow.scoring_tables.list_tables() if t.name == OFFICIAL)
        uow.scoring_tables.set_table_units(table.id, [units["IFCH"]])
        uow.commit()

    seed_unit_defaults(uow_factory())

    assert set(_marks(uow_factory)) == {"IFCH"}
    assert _mark_events(uow_factory, units["FASI"]) == []


def test_without_the_units_the_tables_or_the_version_it_ends_without_error_and_without_marks(
    uow_factory, units
):
    seed_unit_defaults(uow_factory())  # units, but no table yet
    assert _marks(uow_factory) == {}

    with uow_factory() as uow:  # the table, without the version
        uow.scoring_tables.add_table(
            ScoringTableRecord(uuid.uuid4(), OFFICIAL, unit_ids=tuple(units.values()))
        )
        uow.commit()
    seed_unit_defaults(uow_factory())
    assert _marks(uow_factory) == {}


def test_on_an_empty_database_it_ends_without_error(uow_factory):
    seed_unit_defaults(uow_factory())

    assert _marks(uow_factory) == {}


def test_a_superseded_official_version_is_not_marked(uow_factory, units, seeded):
    official = _official_version_id(uow_factory)
    with uow_factory() as uow:
        successor = replace(uow.scoring_tables.get_version(official), id=uuid.uuid4(), name="Nova")
        uow.scoring_tables.add_version(successor)
        uow.scoring_tables.set_superseded(official, successor.id)
        uow.commit()

    seed_unit_defaults(uow_factory())

    assert _marks(uow_factory) == {}


def test_an_archived_official_table_is_not_marked(uow_factory, units, seeded):
    with uow_factory() as uow:
        table = next(t for t in uow.scoring_tables.list_tables() if t.name == OFFICIAL)
        uow.scoring_tables.set_table_archived(table.id, True)
        uow.commit()

    seed_unit_defaults(uow_factory())

    assert _marks(uow_factory) == {}


# --- GTAB-41: the seed leaves alone a legacy table that a person has changed ---------------------


@pytest.fixture
def admin(uow_factory):
    user = User(uuid.uuid4(), "adm-tabelas@ufpa.br", "Adm", Role.ADMIN, "x")
    with uow_factory() as uow:
        uow.users.add(user)
        uow.commit()
    return user


def _legacy_ids(uow_factory, units) -> dict[str, uuid.UUID]:
    return {
        name: _add_legacy_table(uow_factory, units, name, acronym)
        for name, acronym in zip(LEGACY, ("IFCH", "FASI"), strict=True)
    }


def test_a_legacy_table_the_admin_unarchived_and_reassociated_stays_that_way(
    uow_factory, units, admin
):
    ids = _legacy_ids(uow_factory, units)
    seed_scoring_tables(uow_factory())  # the first start archives and detaches both (OFI-09)
    audit = AuditService(SystemClock())
    fasi_table = ids[LEGACY[1]]
    ArchiveScoringTable(uow_factory, audit).execute(admin, fasi_table, False)
    SetTableUnits(uow_factory, audit).execute(admin, fasi_table, [units["FASI"]])

    seed_scoring_tables(uow_factory())
    seed_scoring_tables(uow_factory())  # and a start after it changes nothing either

    table, _, acronyms = _by_table(uow_factory)[LEGACY[1]]
    assert (table.archived, acronyms) == (False, {"FASI"})


def test_a_legacy_table_the_admin_only_unarchived_is_not_archived_again(
    uow_factory, units, admin
):
    ids = _legacy_ids(uow_factory, units)
    seed_scoring_tables(uow_factory())
    ArchiveScoringTable(uow_factory, AuditService(SystemClock())).execute(
        admin, ids[LEGACY[0]], False
    )

    seed_scoring_tables(uow_factory())

    assert _by_table(uow_factory)[LEGACY[0]][0].archived is False


def test_a_legacy_table_whose_units_the_admin_changed_keeps_them_unarchived(
    uow_factory, units, admin
):
    ids = _legacy_ids(uow_factory, units)
    SetTableUnits(uow_factory, AuditService(SystemClock())).execute(
        admin, ids[LEGACY[0]], [units["IFCH"], units["FASI"]]
    )

    seed_scoring_tables(uow_factory())

    table, _, acronyms = _by_table(uow_factory)[LEGACY[0]]
    assert (table.archived, acronyms) == (False, {"IFCH", "FASI"})


def test_the_legacy_table_nobody_touched_is_still_archived_and_detached_beside_one_that_was(
    uow_factory, units, admin
):
    ids = _legacy_ids(uow_factory, units)
    SetTableUnits(uow_factory, AuditService(SystemClock())).execute(
        admin, ids[LEGACY[1]], [units["FASI"], units["IFCH"]]
    )

    seed_scoring_tables(uow_factory())

    tables = _by_table(uow_factory)
    touched, _, touched_units = tables[LEGACY[1]]
    untouched, _, untouched_units = tables[LEGACY[0]]
    assert (touched.archived, touched_units) == (False, {"FASI", "IFCH"})
    assert (untouched.archived, untouched_units) == (True, set())


def test_a_system_event_on_a_legacy_table_does_not_count_as_a_person_changing_it(
    uow_factory, units
):
    ids = _legacy_ids(uow_factory, units)
    with uow_factory() as uow:
        AuditService(SystemClock()).record(
            uow, None, "scoring_table", ids[LEGACY[0]], AuditAction.UPDATE, {}, {"x": 1}
        )
        uow.commit()

    seed_scoring_tables(uow_factory())

    table, _, acronyms = _by_table(uow_factory)[LEGACY[0]]
    assert (table.archived, acronyms) == (True, set())
