"""SEL-08, ATV-13: scoring table and activity repositories on real PostgreSQL."""

import uuid
from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.domain.entities.academic_unit import AcademicUnit, UnitKind
from app.domain.entities.activity import (
    Activity,
    ActivitySource,
    ActivityStatus,
    Candidate,
    Level,
    PeriodPrecision,
)
from app.domain.entities.career import Modality
from app.domain.entities.process import FunctionalProcess, ProcessStatus
from app.domain.entities.scoring import (
    ScoringCriterion,
    ScoringGroup,
    ScoringMode,
    ScoringTableVersion,
    TableStatus,
)
from app.domain.entities.user import Role, User
from app.domain.errors import Conflict, NotFound, StaleVersion
from app.domain.repositories.ports import ScoringTableRecord

D = Decimal
MINIMUMS = {
    "structure": "Res. 4.644/2015-CONSEPE",
    "norm_reference": "Res. 4.644/2015-CONSEPE, art. 12",
    "by_current_class": {"A": 60, "B": 80, "C": 100, "D": 120},
}


@pytest.fixture
def base(uow_factory):
    unit = AcademicUnit(uuid.uuid4(), "Instituto X", "IX", UnitKind.INSTITUTO)
    other_unit = AcademicUnit(uuid.uuid4(), "Instituto Y", "IY", UnitKind.INSTITUTO)
    admin = User(uuid.uuid4(), "admin@ufpa.br", "Admin", Role.ADMIN, "$argon2id$x")
    with uow_factory() as uow:
        structure_id = uow.career_versions.ensure_structure("MAGISTERIO_SUPERIOR", "Magistério")
        for u in (unit, other_unit):
            uow.units.add(u)
        uow.users.add(admin)
        uow.commit()
    return {"unit": unit, "other": other_unit, "admin": admin, "structure_id": structure_id}


def make_version(table_id, name="v1", valid_from=date(2015, 3, 24), valid_to=None):
    criterion = ScoringCriterion(
        2, 2, "Orientação", "por aluno", ScoringMode.POR_UNIDADE,
        unit_points=D("30"), max_points=D("60"), accepted_evidence="Declaração",
        rules="regra", review_note="conferir",
    )  # fmt: skip
    block = ScoringCriterion(
        4, 4, "Curso", "a cada 3 horas", ScoringMode.POR_BLOCO_DE_HORAS,
        unit_points=D("2"), hours_per_block=D("3"),
    )  # fmt: skip
    weekly = ScoringCriterion(
        1, 1, "Aulas", "horas", ScoringMode.CARGA_SEMANAL,
        weeks_per_semester=17, prep_ratio=D("1"),
    )  # fmt: skip
    return ScoringTableVersion(
        table_id=table_id,
        name=name,
        valid_from=valid_from,
        valid_to=valid_to,
        norm_reference="Anexo I",
        status=TableStatus.PENDENTE_VALIDACAO,
        minimums=MINIMUMS,
        notes="nota da versão",
        groups=(
            ScoringGroup(
                1, "Grupo I", counts_in_total=False, max_points=D("10"), criteria=(weekly,)
            ),
            ScoringGroup(2, "Grupo II", criteria=(criterion,)),
            ScoringGroup(4, "Grupo IV", criteria=(block,)),
        ),
        id=uuid.uuid4(),
    )  # fmt: skip


def add_table(uow_factory, base, name="Tabela IX", unit_ids=None):
    table = ScoringTableRecord(uuid.uuid4(), name, unit_ids=tuple(unit_ids or [base["unit"].id]))
    version = make_version(table.id)
    with uow_factory() as uow:
        uow.scoring_tables.add_table(table)
        uow.scoring_tables.add_version(version)
        uow.commit()
    return table, version


def make_process(base) -> FunctionalProcess:
    from app.domain.entities.professor import Professor, Titration, WorkRegime

    professor = Professor(
        id=uuid.uuid4(), full_name="Docente", siape="7654321", titration=Titration.DOUTORADO,
        position="Professor", career_structure_id=base["structure_id"], unit_id=base["unit"].id,
        faculty="IX", campus="C", work_regime=WorkRegime.DE,
    )  # fmt: skip
    base["professor"] = professor
    return FunctionalProcess(
        id=uuid.uuid4(), professor_id=professor.id, unit_id=base["unit"].id,
        modality=Modality.PROMOCAO, current_class="C", current_denomination="Adjunto",
        current_level=4, target_class="D", target_denomination="Associado", target_level=1,
        start_date=date(2022, 11, 23), end_date=date(2024, 11, 23),
        opening_date=date(2025, 3, 10), created_by=base["admin"].id, notes=None,
        resp_name=None, resp_position=None, resp_appointment=None, resp_admin_unit=None,
        status=ProcessStatus.RASCUNHO,
    )  # fmt: skip


def add_process(uow_factory, base) -> FunctionalProcess:
    process = make_process(base)
    with uow_factory() as uow:
        uow.professors.add(base["professor"])
        uow.processes.add(process)
        uow.commit()
    return process


def test_table_and_version_round_trip_with_groups_and_criteria(uow_factory, base):
    table, version = add_table(uow_factory, base)
    with uow_factory() as uow:
        assert uow.scoring_tables.get_table(table.id) == table
        assert [t.id for t in uow.scoring_tables.list_tables()] == [table.id]
        loaded = uow.scoring_tables.get_version(version.id)
        listed = uow.scoring_tables.list_versions(table.id)
    assert loaded == version
    assert loaded.id == version.id
    assert [v.id for v in listed] == [version.id]
    assert loaded.get_criterion(2, 2).unit_points == D("30")
    assert loaded.get_criterion(2, 2).review_note == "conferir"
    assert loaded.get_criterion(4, 4).hours_per_block == D("3")
    assert loaded.get_criterion(1, 1).weeks_per_semester == 17
    assert loaded.get_group(1).counts_in_total is False
    assert loaded.minimums == MINIMUMS
    assert loaded.notes == "nota da versão"


def test_versions_for_unit_only_return_tables_associated_to_it(uow_factory, base):
    table, version = add_table(uow_factory, base)
    add_table(uow_factory, base, name="Tabela IY", unit_ids=[base["other"].id])
    with uow_factory() as uow:
        mine = uow.scoring_tables.list_versions_for_unit(base["unit"].id)
        none = uow.scoring_tables.list_versions_for_unit(uuid.uuid4())
    assert [v.id for v in mine] == [version.id]
    assert none == []


def test_set_table_units_replaces_the_association(uow_factory, base):
    table, _ = add_table(uow_factory, base)
    with uow_factory() as uow:
        uow.scoring_tables.set_table_units(table.id, [base["other"].id])
        uow.commit()
    with uow_factory() as uow:
        assert uow.scoring_tables.get_table(table.id).unit_ids == (base["other"].id,)
        with pytest.raises(NotFound):
            uow.scoring_tables.set_table_units(uuid.uuid4(), [])


def test_duplicate_table_name_raises_conflict(uow_factory, base):
    add_table(uow_factory, base)
    with uow_factory() as uow, pytest.raises(Conflict):
        uow.scoring_tables.add_table(ScoringTableRecord(uuid.uuid4(), "Tabela IX"))


def test_update_version_changes_validity_and_status(uow_factory, base):
    _, version = add_table(uow_factory, base)
    changed = replace(version, valid_to=date(2024, 12, 31), status=TableStatus.OFICIAL)
    with uow_factory() as uow:
        uow.scoring_tables.update_version(changed)
        uow.commit()
    with uow_factory() as uow:
        loaded = uow.scoring_tables.get_version(version.id)
        with pytest.raises(NotFound):
            uow.scoring_tables.update_version(replace(version, id=uuid.uuid4()))
    assert loaded.valid_to == date(2024, 12, 31)
    assert loaded.status is TableStatus.OFICIAL


def test_update_criterion_changes_points_and_rejects_unknown_item(uow_factory, base):
    _, version = add_table(uow_factory, base)
    edited = replace(version.get_criterion(2, 2), unit_points=D("35"), review_note=None)
    with uow_factory() as uow:
        uow.scoring_tables.update_criterion(version.id, edited)
        uow.commit()
    with uow_factory() as uow:
        loaded = uow.scoring_tables.get_version(version.id)
        with pytest.raises(NotFound):
            uow.scoring_tables.update_criterion(version.id, replace(edited, item_number=9))
    assert loaded.get_criterion(2, 2).unit_points == D("35")
    assert loaded.get_criterion(2, 2).review_note is None
    assert loaded.get_criterion(4, 4) == version.get_criterion(4, 4)


def test_version_in_use_only_after_a_process_chooses_it(uow_factory, base):
    _, version = add_table(uow_factory, base)
    process = add_process(uow_factory, base)
    with uow_factory() as uow:
        assert uow.scoring_tables.version_in_use(version.id) is False
        uow.processes.set_scoring_table_version(process.id, version.id)
        uow.commit()
    with uow_factory() as uow:
        assert uow.scoring_tables.version_in_use(version.id) is True
        uow.processes.set_scoring_table_version(process.id, None)
        uow.commit()
    with uow_factory() as uow:
        assert uow.scoring_tables.version_in_use(version.id) is False
        with pytest.raises(NotFound):
            uow.processes.set_scoring_table_version(uuid.uuid4(), version.id)


def make_activity(process, base, **kwargs) -> Activity:
    data = dict(
        id=uuid.uuid4(), process_id=process.id, title="Aula de Cálculo",
        created_by=base["admin"].id,
        group_number=1, item_number=1, description="d", period_start=date(2023, 3, 1),
        period_end=date(2023, 7, 31), period_precision=PeriodPrecision.MONTH,
        academic_period="2023.1", level=Level.GRADUACAO, quantity=D("2.5"), hours=D("68"),
        course_hours=D("60"), informed_points=D("24"), points_override=D("20"),
        unit_points_override=D("2.5"),
        evidence_note="Declaração", source=ActivitySource.IMPORTADA,
        status=ActivityStatus.AGUARDANDO_REVISAO, distinct_justification="outra oferta",
        candidates=(Candidate(2, 3, "talvez"), Candidate(1, 2, "pós")),
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
    )  # fmt: skip
    data.update(kwargs)
    return Activity(**data)


def test_activity_round_trip_with_candidates(uow_factory, base):
    process = add_process(uow_factory, base)
    activity = make_activity(process, base)
    with uow_factory() as uow:
        uow.activities.add(activity)
        uow.commit()
    with uow_factory() as uow:
        loaded = uow.activities.get(activity.id)
    assert loaded is not None and loaded.updated_at is not None
    assert replace(loaded, updated_at=None) == replace(
        activity, candidates=(Candidate(1, 2, "pós"), Candidate(2, 3, "talvez"))
    )
    assert loaded.version == 1


def test_activity_update_bumps_version_and_replaces_candidates(uow_factory, base):
    process = add_process(uow_factory, base)
    activity = make_activity(process, base)
    with uow_factory() as uow:
        uow.activities.add(activity)
        uow.commit()
    with uow_factory() as uow:
        loaded = uow.activities.get(activity.id)
        loaded.title = "Novo título"
        loaded.status = ActivityStatus.VALIDADA
        loaded.candidates = (Candidate(3, 1, "x"),)
        uow.activities.update(loaded, expected_version=1)
        assert loaded.version == 2
        uow.commit()
    with uow_factory() as uow:
        again = uow.activities.get(activity.id)
    assert (again.title, again.status, again.version) == ("Novo título", ActivityStatus.VALIDADA, 2)
    assert again.candidates == (Candidate(3, 1, "x"),)


def test_activity_update_with_stale_version_raises(uow_factory, base):
    process = add_process(uow_factory, base)
    activity = make_activity(process, base)
    with uow_factory() as uow:
        uow.activities.add(activity)
        uow.commit()
    with uow_factory() as uow:
        loaded = uow.activities.get(activity.id)
        uow.activities.update(loaded, expected_version=1)
        uow.commit()
    with uow_factory() as uow:
        stale = uow.activities.get(activity.id)
        stale.title = "Perdida"
        with pytest.raises(StaleVersion):
            uow.activities.update(stale, expected_version=1)
    with uow_factory() as uow:
        assert uow.activities.get(activity.id).title == "Aula de Cálculo"


def test_list_for_process_filters_by_group_and_status(uow_factory, base):
    process = add_process(uow_factory, base)
    a = make_activity(process, base, title="A", candidates=())
    b = make_activity(
        process, base, title="B", group_number=2, item_number=2, status=ActivityStatus.VALIDADA,
        candidates=(), created_at=datetime(2025, 1, 2, tzinfo=UTC),
    )  # fmt: skip
    with uow_factory() as uow:
        uow.activities.add(a)
        uow.activities.add(b)
        uow.commit()
    with uow_factory() as uow:
        everything = uow.activities.list_for_process(process.id)
        group_two = uow.activities.list_for_process(process.id, group_number=2)
        validated = uow.activities.list_for_process(process.id, status=ActivityStatus.VALIDADA)
        pending = uow.activities.list_for_process(
            process.id, group_number=1, status=ActivityStatus.AGUARDANDO_REVISAO
        )
        other = uow.activities.list_for_process(uuid.uuid4())
    assert [x.title for x in everything] == ["A", "B"]
    assert [x.title for x in group_two] == ["B"]
    assert [x.title for x in validated] == ["B"]
    assert [x.title for x in pending] == ["A"]
    assert other == []


def test_version_in_use_ending_from_compares_chosen_process_end_date(uow_factory, base):
    _, version = add_table(uow_factory, base)
    _, other_version = add_table(uow_factory, base, name="Outra")
    process = add_process(uow_factory, base)  # interstice ends 2024-11-23
    with uow_factory() as uow:
        uow.processes.set_scoring_table_version(process.id, version.id)
        uow.commit()
    with uow_factory() as uow:
        repo = uow.scoring_tables
        assert repo.version_in_use_ending_from(version.id, date(2024, 11, 23)) is True
        assert repo.version_in_use_ending_from(version.id, date(2024, 11, 24)) is False
        assert repo.version_in_use_ending_from(version.id, date(2020, 1, 1)) is True
        assert repo.version_in_use_ending_from(other_version.id, date(2020, 1, 1)) is False
