"""NLINK-01, NLINK-02, NTIT-06: the seed links the existing career structures and scoring table
versions to their norms, once, and never overwrites what the ADMIN set."""

import json
import uuid
from dataclasses import replace
from datetime import date

from sqlalchemy import text

from app.domain.entities.career import CareerVersion, Modality
from app.domain.entities.process import FunctionalProcess
from app.domain.entities.professor import Professor, Titration, WorkRegime
from app.domain.entities.user import Role, User
from app.domain.repositories.ports import ScoringTableRecord
from app.domain.rules.career_catalog import LEI_15141_2025, RES_4644_2015
from app.infrastructure.database import seed
from app.infrastructure.database.seed import seed_reference_data, seed_scoring_tables
from tests.integration.test_seed import ADMIN_EMAIL, FakeHasher
from tests.integration.test_seed_scoring import LEGACY, OFFICIAL, _add_legacy_table

STRUCTURE = seed.STRUCTURE_CODE


def _before_the_links(version: CareerVersion) -> CareerVersion:
    """The version as the database held it before this feature: no code, no titration."""
    return replace(
        version,
        norm_code=None,
        required_titration_norm_code=None,
        classes=tuple(replace(c, required_titration=None) for c in version.classes),
    )


def _store_career_versions_before_the_links(uow_factory) -> None:
    """Both structures stored as before this feature, each used by a process."""
    with uow_factory() as uow:
        uow.career_versions.ensure_structure(STRUCTURE, seed.STRUCTURE_NAME)
        for version in (RES_4644_2015, LEI_15141_2025):
            uow.career_versions.add(STRUCTURE, _before_the_links(version))
        campus = seed._ensure_unit(uow, seed.CAMPUS)
        fasi = seed._ensure_unit(uow, seed.FASI, parent_id=campus.id)
        uow.commit()
    units = {"FASI": fasi.id}
    _use_in_a_process(uow_factory, units, date(2024, 11, 23))  # interstice ends under Res. 4.644
    _use_in_a_process(uow_factory, units, date(2026, 11, 23))  # and under the Lei 15.141


def _start(uow_factory) -> None:
    """What the entrypoint runs on every start."""
    seed_reference_data(uow_factory(), ADMIN_EMAIL, "first-password", FakeHasher())
    seed_scoring_tables(uow_factory())


def _versions(uow_factory) -> dict[str, CareerVersion]:
    with uow_factory() as uow:
        return {v.name: v for v in uow.career_versions.list_versions(STRUCTURE)}


def _events(engine, entity: str) -> list:
    with engine.connect() as conn:
        return conn.execute(
            text(
                "SELECT entity_id, action, user_id, changes FROM audit_logs "
                "WHERE entity = :e ORDER BY id"
            ),
            {"e": entity},
        ).all()


def test_the_start_links_the_career_structures_and_the_titration_of_classes_c_and_d(
    engine, uow_factory
):
    _store_career_versions_before_the_links(uow_factory)

    _start(uow_factory)

    versions = _versions(uow_factory)
    old, new = versions[RES_4644_2015.name], versions[LEI_15141_2025.name]
    assert old.norm_code == "RES-4644-2015-CONSEPE"
    assert new.norm_code == "LEI-12772-2012"
    assert {c.code: c.required_titration for c in new.classes} == {
        "A": None,
        "B": None,
        "C": Titration.DOUTORADO,
        "D": Titration.DOUTORADO,
    }
    assert new.required_titration_norm_code == "MANUAL-PROGEP-PROGRESSAO"
    # NTIT-06: the Res. 4.644 structure gets no titration rule
    assert all(c.required_titration is None for c in old.classes)
    assert old.required_titration_norm_code is None
    # the rest of both structures is what it was
    assert _before_the_links(old) == _before_the_links(RES_4644_2015)
    assert _before_the_links(new) == _before_the_links(LEI_15141_2025)


def test_each_linked_career_version_gets_one_system_audit_event(engine, uow_factory):
    _store_career_versions_before_the_links(uow_factory)
    ids = {v.name: v.id for v in _versions(uow_factory).values()}

    _start(uow_factory)

    events = _events(engine, "career_version")
    assert sorted(e.entity_id for e in events) == sorted(str(i) for i in ids.values())
    assert {e.action for e in events} == {"UPDATE"}
    assert {e.user_id for e in events} == {None}
    by_id = {e.entity_id: e.changes for e in events}
    assert by_id[str(ids[RES_4644_2015.name])]["norm_code"] == {
        "before": None,
        "after": "RES-4644-2015-CONSEPE",
    }
    assert "required_titration_norm_code" in by_id[str(ids[LEI_15141_2025.name])]


def test_a_second_start_writes_nothing(engine, uow_factory):
    _store_career_versions_before_the_links(uow_factory)
    _start(uow_factory)
    career_events = _events(engine, "career_version")
    table_events = _events(engine, "scoring_version")
    first = _versions(uow_factory)

    _start(uow_factory)

    assert _events(engine, "career_version") == career_events
    assert _events(engine, "scoring_version") == table_events
    assert _versions(uow_factory) == first


def test_a_value_already_set_by_the_admin_is_not_overwritten(engine, uow_factory):
    _store_career_versions_before_the_links(uow_factory)
    with uow_factory() as uow:
        for version in uow.career_versions.list_versions(STRUCTURE):
            admin_titrations = (
                {"C": Titration.MESTRADO, "D": Titration.MESTRADO}
                if version.name == LEI_15141_2025.name
                else {}
            )
            uow.career_versions.set_links(
                version.id, "NORMA-DO-ADMIN", admin_titrations, "TITULACAO-DO-ADMIN"
            )
        uow.commit()

    _start(uow_factory)

    versions = _versions(uow_factory)
    for version in versions.values():
        assert version.norm_code == "NORMA-DO-ADMIN"
        assert version.required_titration_norm_code == "TITULACAO-DO-ADMIN"
    new = versions[LEI_15141_2025.name]
    assert new.get_class("C").required_titration is Titration.MESTRADO
    assert new.get_class("D").required_titration is Titration.MESTRADO
    assert _events(engine, "career_version") == []


def _data() -> dict:
    return json.loads((seed.SEED_DATA / seed.OFFICIAL_TABLE_SEED).read_text(encoding="utf-8"))


def _units(uow_factory) -> dict[str, uuid.UUID]:
    seed_reference_data(uow_factory(), ADMIN_EMAIL, "first-password", FakeHasher())
    with uow_factory() as uow:
        return {u.acronym: u.id for u in uow.units.list()}


def _store_the_official_table_before_the_links(uow_factory, units) -> uuid.UUID:
    data = _data()
    table = ScoringTableRecord(
        id=uuid.uuid4(), name=data["table_name"], unit_ids=(units["FASI"], units["IFCH"])
    )
    version = replace(seed._scoring_version(data, table.id), norm_code=None)
    with uow_factory() as uow:
        uow.scoring_tables.add_table(table)
        uow.scoring_tables.add_version(version)
        uow.commit()
    return table.id


def _use_in_a_process(uow_factory, units, end_date: date, version_id=None) -> None:
    with uow_factory() as uow:
        admin = User(uuid.uuid4(), f"{uuid.uuid4().hex[:8]}@ufpa.br", "Criador", Role.ADMIN, "x")
        uow.users.add(admin)
        professor = Professor(
            id=uuid.uuid4(), full_name="Docente", siape=str(uuid.uuid4().int)[:7],
            titration=Titration.DOUTORADO, position="Professor do Magistério Superior",
            career_structure_id=uow.career_versions.structure_id(STRUCTURE),
            unit_id=units["FASI"], faculty="FASI", campus="Campus", work_regime=WorkRegime.DE,
        )  # fmt: skip
        uow.professors.add(professor)
        process = FunctionalProcess(
            id=uuid.uuid4(), professor_id=professor.id, unit_id=units["FASI"],
            modality=Modality.PROMOCAO, current_class="C", current_denomination="Adjunto",
            current_level=4, target_class="D", target_denomination="Associado", target_level=1,
            start_date=date(end_date.year - 2, end_date.month, 1), end_date=end_date,
            opening_date=end_date, created_by=admin.id,
        )  # fmt: skip
        uow.processes.add(process)
        if version_id is not None:
            uow.processes.set_scoring_table_version(process.id, version_id)
        uow.commit()


def test_the_official_table_version_in_use_gets_its_code_with_one_system_audit_event(
    engine, uow_factory
):
    units = _units(uow_factory)
    table_id = _store_the_official_table_before_the_links(uow_factory, units)
    with uow_factory() as uow:
        (version,) = uow.scoring_tables.list_versions(table_id)
    _use_in_a_process(uow_factory, units, date(2024, 11, 23), version.id)
    assert version.norm_code is None

    seed_scoring_tables(uow_factory())

    with uow_factory() as uow:
        (linked,) = uow.scoring_tables.list_versions(table_id)
    assert linked.norm_code == "TABELA-OFICIAL-UFPA"
    events = _events(engine, "scoring_version")
    assert [(e.entity_id, e.action, e.user_id) for e in events] == [
        (str(version.id), "UPDATE", None)
    ]
    assert events[0].changes["norm_code"] == {"before": None, "after": "TABELA-OFICIAL-UFPA"}

    seed_scoring_tables(uow_factory())  # a second start writes nothing
    assert _events(engine, "scoring_version") == events


def test_a_table_code_set_by_the_admin_is_not_overwritten(engine, uow_factory):
    units = _units(uow_factory)
    table_id = _store_the_official_table_before_the_links(uow_factory, units)
    with uow_factory() as uow:
        (version,) = uow.scoring_tables.list_versions(table_id)
        uow.scoring_tables.update_version(replace(version, norm_code="CODIGO-DO-ADMIN"))
        uow.commit()

    seed_scoring_tables(uow_factory())

    with uow_factory() as uow:
        (kept,) = uow.scoring_tables.list_versions(table_id)
    assert kept.norm_code == "CODIGO-DO-ADMIN"
    assert _events(engine, "scoring_version") == []


def test_archived_legacy_tables_stay_without_a_code(engine, uow_factory):
    units = _units(uow_factory)
    legacy_ids = [
        _add_legacy_table(uow_factory, units, LEGACY[0], "IFCH"),
        _add_legacy_table(uow_factory, units, LEGACY[1], "FASI"),
    ]

    seed_scoring_tables(uow_factory())

    with uow_factory() as uow:
        tables = {t.name: t for t in uow.scoring_tables.list_tables()}
        for table_id in legacy_ids:
            assert [v.norm_code for v in uow.scoring_tables.list_versions(table_id)] == [None]
    assert tables[LEGACY[0]].archived and tables[LEGACY[1]].archived
    assert [v.norm_code for v in _official_versions(uow_factory)] == ["TABELA-OFICIAL-UFPA"]


def _official_versions(uow_factory):
    with uow_factory() as uow:
        table = next(t for t in uow.scoring_tables.list_tables() if t.name == OFFICIAL)
        return uow.scoring_tables.list_versions(table.id)
