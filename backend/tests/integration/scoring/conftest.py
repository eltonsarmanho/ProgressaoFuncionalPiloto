"""Fixtures for scoring use case tests: seeded units and tables, professors, actors, process."""

import uuid
from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.application.services.access_policy import AccessPolicy
from app.application.services.audit_service import AuditService
from app.application.use_cases import scoring, scoring_admin
from app.domain.entities.career import Modality
from app.domain.entities.process import FunctionalProcess
from app.domain.entities.professor import Professor, Titration, WorkRegime
from app.domain.entities.scoring import ScoringCriterion, ScoringMode, TableStatus
from app.domain.entities.user import Role, User
from app.domain.repositories.ports import ScoringTableRecord
from app.infrastructure.database.seed import seed_reference_data, seed_scoring_tables
from tests.integration.test_seed import FakeHasher


class FixedClock:
    def now(self) -> datetime:
        return datetime(2026, 11, 17, 9, 0, tzinfo=UTC)


def _user(uow, email, role, **kw) -> User:
    user = User(uuid.uuid4(), email, email.split("@")[0], role, "x", **kw)
    uow.users.add(user)
    return user


def _professor(uow, unit, siape, regime=WorkRegime.DE) -> Professor:
    professor = Professor(
        id=uuid.uuid4(),
        full_name=f"Docente {siape}",
        siape=siape,
        titration=Titration.DOUTORADO,
        position="Professor do Magistério Superior",
        career_structure_id=uow.career_versions.structure_id("MAGISTERIO_SUPERIOR"),
        unit_id=unit.id,
        faculty=unit.name,
        campus="Campus",
        work_regime=regime,
    )
    uow.professors.add(professor)
    return professor


def _process(uow, professor, created_by, **kw) -> FunctionalProcess:
    process = FunctionalProcess(
        id=uuid.uuid4(),
        professor_id=professor.id,
        unit_id=professor.unit_id,
        modality=Modality.PROMOCAO,
        current_class="C",
        current_denomination="Adjunto",
        current_level=4,
        target_class="D",
        target_denomination="Associado",
        target_level=1,
        start_date=kw.pop("start_date", date(2022, 11, 23)),
        end_date=kw.pop("end_date", date(2024, 11, 23)),
        opening_date=date(2025, 3, 10),
        created_by=created_by.id,
        **kw,
    )
    uow.processes.add(process)
    return process


OFFICIAL_TABLE = "Tabela de Pontuação da UFPA"
OTHER_TABLE = "Tabela Alternativa de Teste"
POINTS_TABLE = "Tabela de Teste com Grupo I em Pontos"


def _with_criteria(version, group_number, criteria, **group_changes):
    groups = tuple(
        replace(g, criteria=criteria, **group_changes) if g.number == group_number else g
        for g in version.groups
    )
    return replace(version, groups=groups)


def _other_table(uow, official) -> object:
    """A copy of the official version in a table of no unit, differing only in II.12 (10, not 5).

    Stands in for "a table that is not the unit's one": the official table is the only seeded
    table and belongs to both FASI and IFCH. The different II.12 lets a test see a table switch.
    """
    table = ScoringTableRecord(uuid.uuid4(), OTHER_TABLE, unit_ids=())
    uow.scoring_tables.add_table(table)
    group = official.get_group(2)
    criteria = tuple(
        replace(c, unit_points=Decimal("10")) if c.item_number == 12 else c
        for c in group.criteria
    )
    copy = _with_criteria(official, 2, criteria)
    copy = replace(
        copy, id=uuid.uuid4(), table_id=table.id, norm_reference="Tabela de teste, sem norma"
    )
    uow.scoring_tables.add_version(copy)
    return copy


def _points_table(uow, official) -> object:
    """A copy of the official version whose group I counts in points, as the old FASI table.

    Group I keeps the two weekly-load criteria and gets I.3, a VALOR_INFORMADO item limited to
    10 points, so the tests of informed points and limits keep a table that accepts them.
    """
    table = ScoringTableRecord(uuid.uuid4(), POINTS_TABLE, unit_ids=())
    uow.scoring_tables.add_table(table)
    group_one = official.get_group(1)
    informed = ScoringCriterion(
        1, 3, "Avaliação discente (item de teste)", "pontos", ScoringMode.VALOR_INFORMADO,
        max_points=Decimal("10"),
    )  # fmt: skip
    copy = _with_criteria(
        official, 1, (*group_one.criteria, informed), counts_in_total=True
    )
    copy = replace(copy, id=uuid.uuid4(), table_id=table.id, norm_reference="Tabela de teste")
    uow.scoring_tables.add_version(copy)
    return copy


@pytest.fixture
def world(uow_factory):
    seed_reference_data(uow_factory(), "seed-admin@ufpa.br", "x", FakeHasher())
    seed_scoring_tables(uow_factory())
    audit, policy = AuditService(FixedClock()), AccessPolicy()
    with uow_factory() as uow:
        units = {u.acronym: u for u in uow.units.list()}
        fasi, ifch = units["FASI"], units["IFCH"]
        admin = _user(uow, "admin@ufpa.br", Role.ADMIN)
        prof = _professor(uow, fasi, "1000001")
        other_prof = _professor(uow, ifch, "1000002")
        docente = _user(uow, "docente@ufpa.br", Role.DOCENTE, professor_id=prof.id)
        other_docente = _user(uow, "outro@ufpa.br", Role.DOCENTE, professor_id=other_prof.id)
        secretaria = _user(uow, "sec@ufpa.br", Role.SECRETARIA, unit_ids=frozenset({fasi.id}))
        other_secretaria = _user(
            uow, "sec2@ufpa.br", Role.SECRETARIA, unit_ids=frozenset({ifch.id})
        )
        process = _process(uow, prof, admin)
        ifch_process = _process(uow, other_prof, admin)
        official = next(
            uow.scoring_tables.list_versions(t.id)[0]
            for t in uow.scoring_tables.list_tables()
            if t.name == OFFICIAL_TABLE
        )
        other = _other_table(uow, official)
        uow.commit()
    return SimpleNamespace(
        uow_factory=uow_factory,
        audit=audit,
        policy=policy,
        fasi=fasi,
        ifch=ifch,
        admin=admin,
        docente=docente,
        other_docente=other_docente,
        secretaria=secretaria,
        other_secretaria=other_secretaria,
        professor=prof,
        process=process,
        ifch_process=ifch_process,
        official_version=official,
        other_version=other,
        suggest=scoring.SuggestScoringTable(uow_factory, audit, policy),
        choose=scoring.ChooseProcessTable(uow_factory, audit, policy),
        create=scoring.CreateActivity(uow_factory, audit, policy),
        update=scoring.UpdateActivity(uow_factory, audit, policy),
        change_status=scoring.ChangeActivityStatus(uow_factory, audit, policy),
        mark_distinct=scoring.MarkActivitiesDistinct(uow_factory, audit, policy),
        list_activities=scoring.ListActivities(uow_factory, audit, policy),
        calc=scoring.CalculateProcessScore(uow_factory, audit, policy),
    )


@pytest.fixture
def points_chosen(world):
    """A table whose group I counts in points chosen for the main process."""
    with world.uow_factory() as uow:
        world.points_version = _points_table(uow, world.official_version)
        uow.commit()
    world.choose.execute(world.admin, world.process.id, world.points_version.id, None, "Teste")
    return world


def make_official_pending(world) -> None:
    """The official table is OFICIAL; mark it pending, as the old FASI table was."""
    with world.uow_factory() as uow:
        uow.scoring_tables.update_version(
            replace(world.official_version, status=TableStatus.PENDENTE_VALIDACAO)
        )
        uow.commit()


@pytest.fixture
def add_process(world):
    """Persist another process of the FASI professor (custom dates or status)."""

    def add(**kw) -> FunctionalProcess:
        with world.uow_factory() as uow:
            process = _process(uow, world.professor, world.admin, **kw)
            uow.commit()
        return process

    return add


@pytest.fixture
def official_chosen(world):
    """The official table version chosen for the main process."""
    world.choose.execute(world.admin, world.process.id, world.official_version.id, None, None)
    return world


@pytest.fixture
def admin_uc(world):
    """Scoring table administration use cases (phase 6)."""
    uf, audit = world.uow_factory, world.audit
    return SimpleNamespace(
        create_table=scoring_admin.CreateScoringTable(uf, audit),
        duplicate=scoring_admin.DuplicateScoringTable(uf, audit),
        update_criteria=scoring_admin.UpdateVersionCriteria(uf, audit),
        create_version=scoring_admin.CreateVersionFrom(uf, audit),
        import_csv=scoring_admin.ImportCriteriaCsv(uf, audit),
    )
