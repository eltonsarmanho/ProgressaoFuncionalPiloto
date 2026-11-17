"""Fixtures for scoring use case tests: seeded units and tables, professors, actors, process."""

import uuid
from datetime import UTC, date, datetime
from types import SimpleNamespace

import pytest

from app.application.services.access_policy import AccessPolicy
from app.application.services.audit_service import AuditService
from app.application.use_cases import scoring, scoring_admin
from app.domain.entities.career import Modality
from app.domain.entities.process import FunctionalProcess
from app.domain.entities.professor import Professor, Titration, WorkRegime
from app.domain.entities.user import Role, User
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
        tables = {t.name: t for t in uow.scoring_tables.list_tables()}
        versions = {
            name: uow.scoring_tables.list_versions(t.id)[0] for name, t in tables.items()
        }
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
        fasi_version=versions["Tabela de Pontuação da FASI"],
        ifch_version=versions["Tabela de Pontuação do IFCH"],
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
def add_process(world):
    """Persist another process of the FASI professor (custom dates or status)."""

    def add(**kw) -> FunctionalProcess:
        with world.uow_factory() as uow:
            process = _process(uow, world.professor, world.admin, **kw)
            uow.commit()
        return process

    return add


@pytest.fixture
def fasi_chosen(world):
    """The FASI table version chosen for the main process."""
    world.choose.execute(world.admin, world.process.id, world.fasi_version.id, None, None)
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
