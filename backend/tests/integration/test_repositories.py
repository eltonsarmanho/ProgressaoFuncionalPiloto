"""DOC-03 and concurrent-save edge case: SQLAlchemy repositories on real PostgreSQL."""

import uuid
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta

import pytest

from app.domain.entities.academic_unit import AcademicUnit, UnitKind
from app.domain.entities.audit import AuditAction, AuditEvent
from app.domain.entities.career import Modality
from app.domain.entities.process import FunctionalProcess, ProcessStatus
from app.domain.entities.professor import Professor, Titration, WorkRegime
from app.domain.entities.user import Role, User
from app.domain.entities.user import Session as UserSession
from app.domain.errors import Conflict, StaleVersion
from app.domain.rules.career_catalog import MAGISTERIO_SUPERIOR_VERSIONS

T0 = datetime(2026, 11, 16, 12, 0, tzinfo=UTC)


def _unit(**kw) -> AcademicUnit:
    data = dict(id=uuid.uuid4(), name="Faculdade X", acronym="FX", kind=UnitKind.FACULDADE)
    data.update(kw)
    return AcademicUnit(**data)


@pytest.fixture
def base(uow_factory):
    """Persist a structure, a campus, a faculty and an admin user."""
    campus = _unit(name="Campus Y", acronym="CY", kind=UnitKind.CAMPUS)
    faculty = _unit(parent_id=campus.id)
    admin = User(
        id=uuid.uuid4(),
        email="admin@ufpa.br",
        name="Admin",
        role=Role.ADMIN,
        password_hash="$argon2id$x",
    )
    with uow_factory() as uow:
        structure_id = uow.career_versions.ensure_structure("MAGISTERIO_SUPERIOR", "Magistério")
        uow.units.add(campus)
        uow.units.add(faculty)
        uow.users.add(admin)
        uow.commit()
    return {"structure_id": structure_id, "campus": campus, "faculty": faculty, "admin": admin}


def _professor(base, siape="1234567") -> Professor:
    return Professor(
        id=uuid.uuid4(),
        full_name="Docente Teste",
        siape=siape,
        titration=Titration.DOUTORADO,
        position="Professor do Magistério Superior",
        career_structure_id=base["structure_id"],
        unit_id=base["faculty"].id,
        faculty="Faculdade X",
        campus="Campus Y",
        work_regime=WorkRegime.DE,
    )


def _process(base, professor_id) -> FunctionalProcess:
    return FunctionalProcess(
        id=uuid.uuid4(),
        professor_id=professor_id,
        unit_id=base["faculty"].id,
        modality=Modality.PROMOCAO,
        current_class="C",
        current_denomination="Adjunto",
        current_level=4,
        target_class="D",
        target_denomination="Associado",
        target_level=1,
        start_date=date(2022, 11, 23),
        end_date=date(2024, 11, 23),
        opening_date=date(2025, 3, 10),
        created_by=base["admin"].id,
        notes="obs",
        resp_name="Resp",
        resp_position="Diretor",
        resp_appointment="Portaria 1/2025",
        resp_admin_unit="FX",
    )


def test_unit_round_trip_and_update(uow_factory, base):
    with uow_factory() as uow:
        assert uow.units.get(base["faculty"].id) == base["faculty"]
        archived = replace(base["faculty"], archived=True, name="Faculdade Z")
        uow.units.update(archived)
        uow.commit()
    with uow_factory() as uow:
        assert uow.units.get(base["faculty"].id) == archived
        assert {u.id for u in uow.units.list()} == {base["campus"].id, base["faculty"].id}


def test_user_round_trip_with_units(uow_factory, base):
    secretaria = User(
        id=uuid.uuid4(),
        email="Sec@UFPA.br",
        name="Secretaria",
        role=Role.SECRETARIA,
        password_hash="$argon2id$y",
        unit_ids=frozenset({base["faculty"].id}),
    )
    with uow_factory() as uow:
        uow.users.add(secretaria)
        uow.commit()
    with uow_factory() as uow:
        loaded = uow.users.get(secretaria.id)
        by_email = uow.users.get_by_email("sec@ufpa.br")
    assert loaded is not None and loaded.created_at is not None
    assert replace(loaded, created_at=None) == secretaria
    assert by_email == loaded


def test_duplicate_user_email_raises_conflict(uow_factory, base):
    dup = replace(base["admin"], id=uuid.uuid4(), email="ADMIN@ufpa.br")
    with uow_factory() as uow, pytest.raises(Conflict):
        uow.users.add(dup)


def test_session_round_trip_touch_and_delete(uow_factory, base):
    session = UserSession(
        id=uuid.uuid4(),
        user_id=base["admin"].id,
        token_hash="a" * 64,
        csrf_token="csrf-1",
        created_at=T0,
        last_seen_at=T0,
    )
    with uow_factory() as uow:
        uow.sessions.add(session)
        uow.commit()
    with uow_factory() as uow:
        assert uow.sessions.get_by_token_hash("a" * 64) == session
        uow.sessions.touch(session.id, T0 + timedelta(minutes=5))
        uow.commit()
    with uow_factory() as uow:
        assert uow.sessions.get_by_token_hash("a" * 64).last_seen_at == T0 + timedelta(minutes=5)
        uow.sessions.delete(session.id)
        uow.commit()
    with uow_factory() as uow:
        assert uow.sessions.get_by_token_hash("a" * 64) is None


def test_login_attempts_count_failures_since(uow_factory, base):
    with uow_factory() as uow:
        uow.login_attempts.record("x@ufpa.br", T0 - timedelta(minutes=20), False)
        uow.login_attempts.record("x@ufpa.br", T0 - timedelta(minutes=10), False)
        uow.login_attempts.record("x@ufpa.br", T0 - timedelta(minutes=5), True)
        uow.login_attempts.record("X@ufpa.br", T0, False)
        uow.login_attempts.record("y@ufpa.br", T0, False)
        uow.commit()
    with uow_factory() as uow:
        assert uow.login_attempts.count_failures_since("x@ufpa.br", T0 - timedelta(minutes=15)) == 2


def test_professor_round_trip(uow_factory, base):
    professor = _professor(base)
    with uow_factory() as uow:
        uow.professors.add(professor)
        uow.commit()
    with uow_factory() as uow:
        assert uow.professors.get(professor.id) == professor
        assert uow.professors.list() == [professor]


def test_duplicate_siape_raises_conflict_without_creating(uow_factory, base):
    with uow_factory() as uow:
        uow.professors.add(_professor(base))
        uow.commit()
    with uow_factory() as uow:
        with pytest.raises(Conflict):
            uow.professors.add(_professor(base))
        uow.commit()
    with uow_factory() as uow:
        assert len(uow.professors.list()) == 1


def test_professor_update_bumps_version_and_stale_version_is_rejected(uow_factory, base):
    professor = _professor(base)
    with uow_factory() as uow:
        uow.professors.add(professor)
        uow.commit()

    with uow_factory() as first, uow_factory() as second:
        a = first.professors.get(professor.id)
        b = second.professors.get(professor.id)
        a.campus = "Campus W"
        first.professors.update(a, expected_version=1)
        first.commit()
        b.campus = "Campus V"
        with pytest.raises(StaleVersion):
            second.professors.update(b, expected_version=1)

    with uow_factory() as uow:
        saved = uow.professors.get(professor.id)
    assert saved.campus == "Campus W"
    assert saved.version == 2


def test_process_round_trip(uow_factory, base):
    professor = _professor(base)
    process = _process(base, professor.id)
    with uow_factory() as uow:
        uow.professors.add(professor)
        uow.processes.add(process)
        uow.commit()
    with uow_factory() as uow:
        loaded = uow.processes.get(process.id)
        listed = uow.processes.list()
    assert loaded.created_at is not None and loaded.updated_at is not None
    assert replace(loaded, created_at=None, updated_at=None) == process
    assert loaded.status is ProcessStatus.RASCUNHO
    assert listed == [loaded]


def test_process_concurrent_save_first_wins_second_gets_stale_version(uow_factory, base):
    professor = _professor(base)
    process = _process(base, professor.id)
    with uow_factory() as uow:
        uow.professors.add(professor)
        uow.processes.add(process)
        uow.commit()

    with uow_factory() as first, uow_factory() as second:
        a = first.processes.get(process.id)
        b = second.processes.get(process.id)
        a.target_level = 2
        first.processes.update(a, expected_version=1)
        first.commit()
        b.target_level = 3
        with pytest.raises(StaleVersion):
            second.processes.update(b, expected_version=1)

    with uow_factory() as uow:
        saved = uow.processes.get(process.id)
    assert saved.target_level == 2
    assert saved.version == 2


def test_career_versions_round_trip(uow_factory, base):
    with uow_factory() as uow:
        for version in reversed(MAGISTERIO_SUPERIOR_VERSIONS):
            uow.career_versions.add("MAGISTERIO_SUPERIOR", version)
        uow.commit()
    with uow_factory() as uow:
        assert tuple(uow.career_versions.list_versions("MAGISTERIO_SUPERIOR")) == (
            MAGISTERIO_SUPERIOR_VERSIONS
        )


def test_audit_events_round_trip_in_chronological_order(uow_factory, base):
    entity_id = str(uuid.uuid4())
    later = AuditEvent(
        occurred_at=T0 + timedelta(minutes=1),
        user_id=base["admin"].id,
        entity="process",
        entity_id=entity_id,
        action=AuditAction.UPDATE,
        changes={"target_level": {"before": 1, "after": 2}},
        justification="Correção",
    )
    earlier = replace(later, occurred_at=T0, action=AuditAction.CREATE, justification=None)
    with uow_factory() as uow:
        uow.audit.add(later)
        uow.audit.add(earlier)
        uow.audit.add(replace(earlier, entity_id=str(uuid.uuid4())))
        uow.commit()
    with uow_factory() as uow:
        events = uow.audit.list_for("process", entity_id)
    assert [replace(e, id=None) for e in events] == [earlier, later]
