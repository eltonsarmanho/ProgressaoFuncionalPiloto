"""SQLAlchemy implementations of the domain ports (AD-001)."""

import uuid
from collections.abc import Sequence
from dataclasses import asdict
from datetime import date, datetime
from types import TracebackType
from typing import Any, Self
from uuid import UUID

from sqlalchemy import Table, delete, exists, func, insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.domain.entities.academic_unit import AcademicUnit
from app.domain.entities.activity import Activity, ActivityStatus, Candidate
from app.domain.entities.audit import AuditEvent
from app.domain.entities.career import CareerClass, CareerVersion
from app.domain.entities.process import FunctionalProcess
from app.domain.entities.professor import Professor
from app.domain.entities.scoring import (
    ScoringCriterion,
    ScoringGroup,
    ScoringTableVersion,
)
from app.domain.entities.user import Session as UserSession
from app.domain.entities.user import User
from app.domain.errors import Conflict, NotFound, StaleVersion
from app.domain.repositories.ports import ScoringTableRecord
from app.infrastructure.database.models import (
    AcademicUnitModel,
    ActivityCandidateModel,
    ActivityModel,
    AuditLogModel,
    CareerStructureModel,
    CareerVersionModel,
    FunctionalProcessModel,
    LoginAttemptModel,
    ProfessorModel,
    ScoringCriterionModel,
    ScoringGroupModel,
    ScoringTableModel,
    ScoringTableUnitModel,
    ScoringTableVersionModel,
    SessionModel,
    UserModel,
    UserUnitModel,
)

UNIQUE_VIOLATION = "23505"


def _is_unique_violation(exc: IntegrityError) -> bool:
    return getattr(exc.orig, "sqlstate", None) == UNIQUE_VIOLATION


def _insert(session: Session, table: Table, values: dict[str, Any], what: str) -> None:
    """Insert inside a savepoint; a unique violation becomes Conflict."""
    try:
        with session.begin_nested():
            session.execute(insert(table).values(**values))
    except IntegrityError as exc:
        if _is_unique_violation(exc):
            raise Conflict(f"{what} já cadastrado") from None
        raise


def _versioned_update(
    session: Session,
    model: type[ProfessorModel] | type[FunctionalProcessModel] | type[ActivityModel],
    entity_id: UUID,
    expected_version: int,
    values: dict[str, Any],
    what: str,
) -> int:
    """Optimistic lock: update only if the row still has expected_version."""
    new_version = expected_version + 1
    stmt = (
        update(model)
        .where(model.id == entity_id, model.version == expected_version)
        .values(**values, version=new_version)
    )
    try:
        with session.begin_nested():
            rowcount = session.execute(stmt).rowcount
    except IntegrityError as exc:
        if _is_unique_violation(exc):
            raise Conflict(f"{what} já cadastrado") from None
        raise
    if rowcount == 0:
        if session.get(model, entity_id) is None:
            raise NotFound(f"{what} não encontrado")
        raise StaleVersion(f"{what} foi alterado por outro usuário; recarregue")
    return new_version


class SqlUserRepository:
    def __init__(self, session: Session):
        self._s = session

    def _to_entity(self, m: UserModel) -> User:
        unit_ids = self._s.scalars(
            select(UserUnitModel.unit_id).where(UserUnitModel.user_id == m.id)
        ).all()
        return User(
            id=m.id,
            email=m.email,
            name=m.name,
            role=m.role,
            password_hash=m.password_hash,
            professor_id=m.professor_id,
            active=m.active,
            unit_ids=frozenset(unit_ids),
            created_at=m.created_at,
        )

    def get(self, user_id: UUID) -> User | None:
        m = self._s.get(UserModel, user_id)
        return self._to_entity(m) if m else None

    def get_by_email(self, email: str) -> User | None:
        m = self._s.scalars(select(UserModel).where(UserModel.email == email)).first()
        return self._to_entity(m) if m else None

    def add(self, user: User) -> None:
        values = {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "password_hash": user.password_hash,
            "professor_id": user.professor_id,
            "active": user.active,
        }
        if user.created_at is not None:
            values["created_at"] = user.created_at
        _insert(self._s, UserModel.__table__, values, "Usuário")
        for unit_id in user.unit_ids:
            self._s.execute(insert(UserUnitModel).values(user_id=user.id, unit_id=unit_id))

    def list(self) -> Sequence[User]:
        models = self._s.scalars(select(UserModel).order_by(UserModel.name)).all()
        return [self._to_entity(m) for m in models]


class SqlSessionRepository:
    def __init__(self, session: Session):
        self._s = session

    def get_by_token_hash(self, token_hash: str) -> UserSession | None:
        m = self._s.scalars(
            select(SessionModel).where(SessionModel.token_hash == token_hash)
        ).first()
        if m is None:
            return None
        return UserSession(
            id=m.id,
            user_id=m.user_id,
            token_hash=m.token_hash,
            csrf_token=m.csrf_token,
            created_at=m.created_at,
            last_seen_at=m.last_seen_at,
        )

    def add(self, session: UserSession) -> None:
        _insert(self._s, SessionModel.__table__, asdict(session), "Sessão")

    def touch(self, session_id: UUID, last_seen_at: datetime) -> None:
        self._s.execute(
            update(SessionModel)
            .where(SessionModel.id == session_id)
            .values(last_seen_at=last_seen_at)
        )

    def delete(self, session_id: UUID) -> None:
        self._s.execute(delete(SessionModel).where(SessionModel.id == session_id))


class SqlLoginAttemptRepository:
    def __init__(self, session: Session):
        self._s = session

    def record(self, email: str, attempted_at: datetime, success: bool) -> None:
        self._s.execute(
            insert(LoginAttemptModel).values(
                email=email, attempted_at=attempted_at, success=success
            )
        )

    def count_failures_since(self, email: str, since: datetime) -> int:
        return self._s.scalar(
            select(func.count())
            .select_from(LoginAttemptModel)
            .where(
                LoginAttemptModel.email == email,
                LoginAttemptModel.success.is_(False),
                LoginAttemptModel.attempted_at >= since,
            )
        )


_PROFESSOR_FIELDS = (
    "full_name",
    "siape",
    "titration",
    "position",
    "career_structure_id",
    "unit_id",
    "faculty",
    "campus",
    "work_regime",
    "archived",
)


class SqlProfessorRepository:
    def __init__(self, session: Session):
        self._s = session

    @staticmethod
    def _to_entity(m: ProfessorModel) -> Professor:
        return Professor(
            id=m.id, version=m.version, **{f: getattr(m, f) for f in _PROFESSOR_FIELDS}
        )

    def get(self, professor_id: UUID) -> Professor | None:
        m = self._s.get(ProfessorModel, professor_id, populate_existing=True)
        return self._to_entity(m) if m else None

    def add(self, professor: Professor) -> None:
        _insert(self._s, ProfessorModel.__table__, asdict(professor), "SIAPE")

    def update(self, professor: Professor, expected_version: int) -> None:
        values = {f: getattr(professor, f) for f in _PROFESSOR_FIELDS}
        professor.version = _versioned_update(
            self._s, ProfessorModel, professor.id, expected_version, values, "SIAPE"
        )

    def list(self) -> Sequence[Professor]:
        models = self._s.scalars(select(ProfessorModel).order_by(ProfessorModel.full_name)).all()
        return [self._to_entity(m) for m in models]


_PROCESS_FIELDS = (
    "professor_id",
    "unit_id",
    "modality",
    "current_class",
    "current_denomination",
    "current_level",
    "target_class",
    "target_denomination",
    "target_level",
    "start_date",
    "end_date",
    "opening_date",
    "created_by",
    "status",
    "notes",
    "resp_name",
    "resp_position",
    "resp_appointment",
    "resp_admin_unit",
)


class SqlProcessRepository:
    def __init__(self, session: Session):
        self._s = session

    @staticmethod
    def _to_entity(m: FunctionalProcessModel) -> FunctionalProcess:
        return FunctionalProcess(
            id=m.id,
            created_at=m.created_at,
            updated_at=m.updated_at,
            version=m.version,
            scoring_table_version_id=m.scoring_table_version_id,
            **{f: getattr(m, f) for f in _PROCESS_FIELDS},
        )

    def get(self, process_id: UUID) -> FunctionalProcess | None:
        m = self._s.get(FunctionalProcessModel, process_id, populate_existing=True)
        return self._to_entity(m) if m else None

    def add(self, process: FunctionalProcess) -> None:
        values = {f: getattr(process, f) for f in _PROCESS_FIELDS}
        values.update(id=process.id, version=process.version)
        for stamp in ("created_at", "updated_at"):
            if getattr(process, stamp) is not None:
                values[stamp] = getattr(process, stamp)
        _insert(self._s, FunctionalProcessModel.__table__, values, "Processo")

    def update(self, process: FunctionalProcess, expected_version: int) -> None:
        values = {f: getattr(process, f) for f in _PROCESS_FIELDS}
        values["updated_at"] = func.now()
        process.version = _versioned_update(
            self._s, FunctionalProcessModel, process.id, expected_version, values, "Processo"
        )

    def list(self) -> Sequence[FunctionalProcess]:
        models = self._s.scalars(
            select(FunctionalProcessModel).order_by(FunctionalProcessModel.created_at)
        ).all()
        return [self._to_entity(m) for m in models]

    def set_scoring_table_version(self, process_id: UUID, version_id: UUID | None) -> None:
        rowcount = self._s.execute(
            update(FunctionalProcessModel)
            .where(FunctionalProcessModel.id == process_id)
            .values(scoring_table_version_id=version_id)
        ).rowcount
        if rowcount == 0:
            raise NotFound("Processo não encontrado")


class SqlAcademicUnitRepository:
    def __init__(self, session: Session):
        self._s = session

    @staticmethod
    def _to_entity(m: AcademicUnitModel) -> AcademicUnit:
        return AcademicUnit(
            id=m.id,
            name=m.name,
            acronym=m.acronym,
            kind=m.kind,
            parent_id=m.parent_id,
            archived=m.archived,
        )

    def get(self, unit_id: UUID) -> AcademicUnit | None:
        m = self._s.get(AcademicUnitModel, unit_id, populate_existing=True)
        return self._to_entity(m) if m else None

    def add(self, unit: AcademicUnit) -> None:
        _insert(self._s, AcademicUnitModel.__table__, asdict(unit), "Unidade")

    def update(self, unit: AcademicUnit) -> None:
        values = asdict(unit)
        unit_id = values.pop("id")
        rowcount = self._s.execute(
            update(AcademicUnitModel).where(AcademicUnitModel.id == unit_id).values(**values)
        ).rowcount
        if rowcount == 0:
            raise NotFound("Unidade não encontrada")

    def list(self) -> Sequence[AcademicUnit]:
        models = self._s.scalars(select(AcademicUnitModel).order_by(AcademicUnitModel.name)).all()
        return [self._to_entity(m) for m in models]


def career_definition(version: CareerVersion) -> dict[str, Any]:
    """JSONB `definition` of a career version (design.md, Data Models)."""
    return {
        "progression_min_months": version.progression_min_months,
        "classes": [
            {
                "code": c.code,
                "denominations": list(c.denominations),
                "levels": list(c.levels),
                "promotion_min_months": c.promotion_min_months,
            }
            for c in version.classes
        ],
    }


def _career_version(m: CareerVersionModel) -> CareerVersion:
    definition = m.definition
    return CareerVersion(
        id=m.id,
        name=m.name,
        valid_from=m.valid_from,
        valid_to=m.valid_to,
        norm_reference=m.norm_reference,
        progression_min_months=definition["progression_min_months"],
        classes=tuple(
            CareerClass(
                code=c["code"],
                denominations=tuple(c["denominations"]),
                levels=tuple(c["levels"]),
                promotion_min_months=c["promotion_min_months"],
            )
            for c in definition["classes"]
        ),
    )


class SqlCareerVersionRepository:
    def __init__(self, session: Session):
        self._s = session

    def ensure_structure(self, code: str, name: str) -> UUID:
        """Return the structure id, creating it when missing (used by the seed)."""
        existing = self._s.scalar(
            select(CareerStructureModel.id).where(CareerStructureModel.code == code)
        )
        if existing is not None:
            return existing
        structure_id = uuid.uuid4()
        _insert(
            self._s,
            CareerStructureModel.__table__,
            {"id": structure_id, "code": code, "name": name},
            "Estrutura de carreira",
        )
        return structure_id

    def structure_id(self, structure_code: str) -> UUID | None:
        return self._s.scalar(
            select(CareerStructureModel.id).where(CareerStructureModel.code == structure_code)
        )

    def structure_code(self, structure_id: UUID) -> str | None:
        return self._s.scalar(
            select(CareerStructureModel.code).where(CareerStructureModel.id == structure_id)
        )

    def list_versions(self, structure_code: str) -> Sequence[CareerVersion]:
        models = self._s.scalars(
            select(CareerVersionModel)
            .join(CareerStructureModel, CareerStructureModel.id == CareerVersionModel.structure_id)
            .where(CareerStructureModel.code == structure_code)
            .order_by(CareerVersionModel.valid_from.asc().nulls_first())
        ).all()
        return [_career_version(m) for m in models]

    def add(self, structure_code: str, version: CareerVersion) -> None:
        structure_id = self._s.scalar(
            select(CareerStructureModel.id).where(CareerStructureModel.code == structure_code)
        )
        if structure_id is None:
            raise NotFound("Estrutura de carreira não encontrada")
        self._s.execute(
            insert(CareerVersionModel).values(
                id=version.id or uuid.uuid4(),
                structure_id=structure_id,
                name=version.name,
                valid_from=version.valid_from,
                valid_to=version.valid_to,
                norm_reference=version.norm_reference,
                definition=career_definition(version),
            )
        )

    def update(self, version: CareerVersion) -> None:
        rowcount = self._s.execute(
            update(CareerVersionModel)
            .where(CareerVersionModel.id == version.id)
            .values(
                name=version.name,
                valid_from=version.valid_from,
                valid_to=version.valid_to,
                norm_reference=version.norm_reference,
                definition=career_definition(version),
            )
        ).rowcount
        if rowcount == 0:
            raise NotFound("Versão de carreira não encontrada")


_CRITERION_FIELDS = (
    "description",
    "unit_label",
    "mode",
    "unit_points",
    "hours_per_block",
    "weeks_per_semester",
    "prep_ratio",
    "max_points",
    "accepted_evidence",
    "rules",
    "review_note",
)


def _criterion_entity(group_number: int, m: ScoringCriterionModel) -> ScoringCriterion:
    return ScoringCriterion(
        group_number=group_number,
        item_number=m.item_number,
        **{f: getattr(m, f) for f in _CRITERION_FIELDS},
    )


class SqlScoringTableRepository:
    def __init__(self, session: Session):
        self._s = session

    def _record(self, m: ScoringTableModel) -> ScoringTableRecord:
        unit_ids = self._s.scalars(
            select(ScoringTableUnitModel.unit_id).where(ScoringTableUnitModel.table_id == m.id)
        ).all()
        return ScoringTableRecord(
            id=m.id, name=m.name, archived=m.archived, unit_ids=tuple(sorted(unit_ids))
        )

    def list_tables(self) -> Sequence[ScoringTableRecord]:
        models = self._s.scalars(select(ScoringTableModel).order_by(ScoringTableModel.name)).all()
        return [self._record(m) for m in models]

    def get_table(self, table_id: UUID) -> ScoringTableRecord | None:
        m = self._s.get(ScoringTableModel, table_id, populate_existing=True)
        return self._record(m) if m else None

    def add_table(self, table: ScoringTableRecord) -> None:
        _insert(
            self._s,
            ScoringTableModel.__table__,
            {"id": table.id, "name": table.name, "archived": table.archived},
            "Tabela de pontuação",
        )
        self._insert_units(table.id, table.unit_ids)

    def _insert_units(self, table_id: UUID, unit_ids: Sequence[UUID]) -> None:
        for unit_id in dict.fromkeys(unit_ids):
            self._s.execute(
                insert(ScoringTableUnitModel).values(table_id=table_id, unit_id=unit_id)
            )

    def set_table_units(self, table_id: UUID, unit_ids: Sequence[UUID]) -> None:
        if self._s.get(ScoringTableModel, table_id) is None:
            raise NotFound("Tabela de pontuação não encontrada")
        self._s.execute(
            delete(ScoringTableUnitModel).where(ScoringTableUnitModel.table_id == table_id)
        )
        self._insert_units(table_id, unit_ids)

    def _versions(self, models: Sequence[ScoringTableVersionModel]) -> list[ScoringTableVersion]:
        result = []
        for m in models:
            groups = self._s.scalars(
                select(ScoringGroupModel)
                .where(ScoringGroupModel.version_id == m.id)
                .order_by(ScoringGroupModel.number)
            ).all()
            entities = []
            for g in groups:
                criteria = self._s.scalars(
                    select(ScoringCriterionModel)
                    .where(ScoringCriterionModel.group_id == g.id)
                    .order_by(ScoringCriterionModel.item_number)
                ).all()
                entities.append(
                    ScoringGroup(
                        number=g.number,
                        name=g.name,
                        counts_in_total=g.counts_in_total,
                        max_points=g.max_points,
                        criteria=tuple(_criterion_entity(g.number, c) for c in criteria),
                    )
                )
            result.append(
                ScoringTableVersion(
                    id=m.id,
                    table_id=m.table_id,
                    name=m.name,
                    valid_from=m.valid_from,
                    valid_to=m.valid_to,
                    norm_reference=m.norm_reference,
                    status=m.status,
                    minimums=m.minimums,
                    notes=m.notes,
                    groups=tuple(entities),
                )
            )
        return result

    def list_versions(self, table_id: UUID) -> Sequence[ScoringTableVersion]:
        models = self._s.scalars(
            select(ScoringTableVersionModel)
            .where(ScoringTableVersionModel.table_id == table_id)
            .order_by(ScoringTableVersionModel.valid_from)
        ).all()
        return self._versions(models)

    def list_versions_for_unit(self, unit_id: UUID) -> Sequence[ScoringTableVersion]:
        models = self._s.scalars(
            select(ScoringTableVersionModel)
            .join(
                ScoringTableUnitModel,
                ScoringTableUnitModel.table_id == ScoringTableVersionModel.table_id,
            )
            .where(ScoringTableUnitModel.unit_id == unit_id)
            .order_by(ScoringTableVersionModel.valid_from)
        ).all()
        return self._versions(models)

    def get_version(self, version_id: UUID) -> ScoringTableVersion | None:
        m = self._s.get(ScoringTableVersionModel, version_id, populate_existing=True)
        return self._versions([m])[0] if m else None

    def add_version(self, version: ScoringTableVersion) -> None:
        if version.table_id is None or self._s.get(ScoringTableModel, version.table_id) is None:
            raise NotFound("Tabela de pontuação não encontrada")
        version_id = version.id or uuid.uuid4()
        self._s.execute(
            insert(ScoringTableVersionModel).values(
                id=version_id,
                table_id=version.table_id,
                name=version.name,
                valid_from=version.valid_from,
                valid_to=version.valid_to,
                norm_reference=version.norm_reference,
                status=version.status,
                minimums=version.minimums,
                notes=version.notes,
            )
        )
        for group in version.groups:
            group_id = uuid.uuid4()
            self._s.execute(
                insert(ScoringGroupModel).values(
                    id=group_id,
                    version_id=version_id,
                    number=group.number,
                    name=group.name,
                    counts_in_total=group.counts_in_total,
                    max_points=group.max_points,
                )
            )
            for c in group.criteria:
                self._s.execute(
                    insert(ScoringCriterionModel).values(
                        id=uuid.uuid4(),
                        group_id=group_id,
                        item_number=c.item_number,
                        **{f: getattr(c, f) for f in _CRITERION_FIELDS},
                    )
                )

    def update_version(self, version: ScoringTableVersion) -> None:
        """Update the version-level fields; groups and criteria change via update_criterion."""
        rowcount = self._s.execute(
            update(ScoringTableVersionModel)
            .where(ScoringTableVersionModel.id == version.id)
            .values(
                name=version.name,
                valid_from=version.valid_from,
                valid_to=version.valid_to,
                norm_reference=version.norm_reference,
                status=version.status,
                minimums=version.minimums,
                notes=version.notes,
            )
        ).rowcount
        if rowcount == 0:
            raise NotFound("Versão da tabela não encontrada")

    def update_criterion(self, version_id: UUID, criterion: ScoringCriterion) -> None:
        group_id = self._s.scalar(
            select(ScoringGroupModel.id).where(
                ScoringGroupModel.version_id == version_id,
                ScoringGroupModel.number == criterion.group_number,
            )
        )
        rowcount = 0
        if group_id is not None:
            rowcount = self._s.execute(
                update(ScoringCriterionModel)
                .where(
                    ScoringCriterionModel.group_id == group_id,
                    ScoringCriterionModel.item_number == criterion.item_number,
                )
                .values(**{f: getattr(criterion, f) for f in _CRITERION_FIELDS})
            ).rowcount
        if rowcount == 0:
            raise NotFound("Critério não encontrado")

    def version_in_use(self, version_id: UUID) -> bool:
        return bool(
            self._s.scalar(
                select(
                    exists().where(FunctionalProcessModel.scoring_table_version_id == version_id)
                )
            )
        )

    def version_in_use_ending_from(self, version_id: UUID, moment: date) -> bool:
        return bool(
            self._s.scalar(
                select(
                    exists().where(
                        FunctionalProcessModel.scoring_table_version_id == version_id,
                        FunctionalProcessModel.end_date >= moment,
                    )
                )
            )
        )


_ACTIVITY_FIELDS = (
    "process_id",
    "group_number",
    "item_number",
    "title",
    "description",
    "event_date",
    "period_start",
    "period_end",
    "period_precision",
    "academic_period",
    "level",
    "quantity",
    "hours",
    "course_hours",
    "informed_points",
    "points_override",
    "evidence_note",
    "source",
    "status",
    "distinct_justification",
    "created_by",
)


class SqlActivityRepository:
    def __init__(self, session: Session):
        self._s = session

    def _to_entity(self, m: ActivityModel) -> Activity:
        candidates = self._s.scalars(
            select(ActivityCandidateModel)
            .where(ActivityCandidateModel.activity_id == m.id)
            .order_by(ActivityCandidateModel.group_number, ActivityCandidateModel.item_number)
        ).all()
        return Activity(
            id=m.id,
            created_at=m.created_at,
            updated_at=m.updated_at,
            version=m.version,
            candidates=tuple(
                Candidate(c.group_number, c.item_number, c.justification) for c in candidates
            ),
            **{f: getattr(m, f) for f in _ACTIVITY_FIELDS},
        )

    def _replace_candidates(self, activity: Activity) -> None:
        self._s.execute(
            delete(ActivityCandidateModel).where(ActivityCandidateModel.activity_id == activity.id)
        )
        for c in activity.candidates:
            self._s.execute(
                insert(ActivityCandidateModel).values(
                    activity_id=activity.id,
                    group_number=c.group_number,
                    item_number=c.item_number,
                    justification=c.justification,
                )
            )

    def get(self, activity_id: UUID) -> Activity | None:
        m = self._s.get(ActivityModel, activity_id, populate_existing=True)
        return self._to_entity(m) if m else None

    def add(self, activity: Activity) -> None:
        values = {f: getattr(activity, f) for f in _ACTIVITY_FIELDS}
        values.update(id=activity.id, version=activity.version)
        for stamp in ("created_at", "updated_at"):
            if getattr(activity, stamp) is not None:
                values[stamp] = getattr(activity, stamp)
        _insert(self._s, ActivityModel.__table__, values, "Atividade")
        self._replace_candidates(activity)

    def update(self, activity: Activity, expected_version: int) -> None:
        values = {f: getattr(activity, f) for f in _ACTIVITY_FIELDS}
        values["updated_at"] = func.now()
        activity.version = _versioned_update(
            self._s, ActivityModel, activity.id, expected_version, values, "Atividade"
        )
        self._replace_candidates(activity)

    def list_for_process(
        self,
        process_id: UUID,
        group_number: int | None = None,
        status: ActivityStatus | None = None,
    ) -> Sequence[Activity]:
        stmt = select(ActivityModel).where(ActivityModel.process_id == process_id)
        if group_number is not None:
            stmt = stmt.where(ActivityModel.group_number == group_number)
        if status is not None:
            stmt = stmt.where(ActivityModel.status == status)
        models = self._s.scalars(stmt.order_by(ActivityModel.created_at, ActivityModel.id)).all()
        return [self._to_entity(m) for m in models]


class SqlAuditRepository:
    def __init__(self, session: Session):
        self._s = session

    def add(self, event: AuditEvent) -> None:
        values = asdict(event)
        values.pop("id")
        self._s.execute(insert(AuditLogModel).values(**values))

    def list_for(self, entity: str, entity_id: str) -> Sequence[AuditEvent]:
        models = self._s.scalars(
            select(AuditLogModel)
            .where(AuditLogModel.entity == entity, AuditLogModel.entity_id == entity_id)
            .order_by(AuditLogModel.occurred_at, AuditLogModel.id)
        ).all()
        return [
            AuditEvent(
                id=m.id,
                occurred_at=m.occurred_at,
                user_id=m.user_id,
                entity=m.entity,
                entity_id=m.entity_id,
                action=m.action,
                changes=m.changes,
                justification=m.justification,
            )
            for m in models
        ]


class SqlUnitOfWork:
    """One SQLAlchemy session per unit of work; rolls back unless committed."""

    def __init__(self, session_factory: sessionmaker[Session]):
        self._factory = session_factory

    def __enter__(self) -> Self:
        self._session = self._factory()
        self.users = SqlUserRepository(self._session)
        self.sessions = SqlSessionRepository(self._session)
        self.login_attempts = SqlLoginAttemptRepository(self._session)
        self.professors = SqlProfessorRepository(self._session)
        self.processes = SqlProcessRepository(self._session)
        self.units = SqlAcademicUnitRepository(self._session)
        self.career_versions = SqlCareerVersionRepository(self._session)
        self.scoring_tables = SqlScoringTableRepository(self._session)
        self.activities = SqlActivityRepository(self._session)
        self.audit = SqlAuditRepository(self._session)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self._session.rollback()
        self._session.close()

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()
