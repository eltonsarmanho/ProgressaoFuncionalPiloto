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
from app.domain.entities.document import (
    Document,
    DocumentStatus,
    ExtractionRun,
    PageText,
    RunStatus,
)
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
from app.domain.repositories.ports import (
    DEFAULT_MAX_JOB_ATTEMPTS,
    EXHAUSTED_CODE,
    ActivityEvidence,
    JobStatus,
    ProcessingJob,
    ScoringTableRecord,
)
from app.infrastructure.database.models import (
    AcademicUnitModel,
    ActivityCandidateModel,
    ActivityEvidenceModel,
    ActivityModel,
    AuditLogModel,
    CareerStructureModel,
    CareerVersionModel,
    DocumentModel,
    DocumentPageModel,
    ExtractionRunModel,
    FunctionalProcessModel,
    LoginAttemptModel,
    ProcessingJobModel,
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
    model: type[ProfessorModel]
    | type[FunctionalProcessModel]
    | type[ActivityModel]
    | type[DocumentModel],
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
    "min_hours",
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

    def set_table_archived(self, table_id: UUID, archived: bool) -> None:
        model = self._s.get(ScoringTableModel, table_id)
        if model is None:
            raise NotFound("Tabela de pontuação não encontrada")
        model.archived = archived

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
    "extraction_run_id",
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


_DOCUMENT_FIELDS = (
    "process_id",
    "original_name",
    "internal_name",
    "mime",
    "size_bytes",
    "sha256",
    "page_count",
    "status",
    "status_code",
    "manual_type",
    "manual_category",
    "suggested_type",
    "suggested_category",
    "confidence",
    "uploaded_by",
)
# Columns a document update may change; the owner, process and upload time never change.
_DOCUMENT_UPDATABLE = tuple(f for f in _DOCUMENT_FIELDS if f not in ("process_id", "uploaded_by"))


class SqlDocumentRepository:
    def __init__(self, session: Session):
        self._s = session

    @staticmethod
    def _to_entity(m: DocumentModel) -> Document:
        return Document(
            id=m.id,
            uploaded_at=m.uploaded_at,
            version=m.version,
            updated_at=m.updated_at,
            **{f: getattr(m, f) for f in _DOCUMENT_FIELDS},
        )

    def get(self, document_id: UUID) -> Document | None:
        m = self._s.get(DocumentModel, document_id, populate_existing=True)
        return self._to_entity(m) if m else None

    def add(self, document: Document) -> None:
        values = {f: getattr(document, f) for f in _DOCUMENT_FIELDS}
        values.update(id=document.id, version=document.version)
        if document.uploaded_at is not None:
            values["uploaded_at"] = document.uploaded_at
        try:
            with self._s.begin_nested():
                self._s.execute(insert(DocumentModel.__table__).values(**values))
        except IntegrityError as exc:
            if not _is_unique_violation(exc):
                raise
            existing = self.exists_hash(document.process_id, document.sha256)
            if existing is not None:
                raise Conflict(
                    f"Arquivo já enviado neste processo (documento {existing})"
                ) from None
            raise Conflict("Documento já cadastrado") from None

    def update(self, document: Document, expected_version: int) -> None:
        values = {f: getattr(document, f) for f in _DOCUMENT_UPDATABLE}
        values["updated_at"] = func.now()
        document.version = _versioned_update(
            self._s, DocumentModel, document.id, expected_version, values, "Documento"
        )

    def list_for_process(
        self,
        process_id: UUID,
        status: DocumentStatus | None = None,
        document_type: str | None = None,
    ) -> Sequence[Document]:
        stmt = select(DocumentModel).where(DocumentModel.process_id == process_id)
        if status is not None:
            stmt = stmt.where(DocumentModel.status == status)
        if document_type is not None:
            effective = func.coalesce(DocumentModel.manual_type, DocumentModel.suggested_type)
            stmt = stmt.where(effective == document_type)
        models = self._s.scalars(stmt.order_by(DocumentModel.uploaded_at, DocumentModel.id)).all()
        return [self._to_entity(m) for m in models]

    def exists_hash(self, process_id: UUID, sha256: str) -> UUID | None:
        return self._s.scalar(
            select(DocumentModel.id).where(
                DocumentModel.process_id == process_id, DocumentModel.sha256 == sha256
            )
        )

    def delete(self, document_id: UUID) -> None:
        """Pages, runs, jobs and links go with it (cascade); activities stay (DOC-10)."""
        rowcount = self._s.execute(
            delete(DocumentModel).where(DocumentModel.id == document_id)
        ).rowcount
        if rowcount == 0:
            raise NotFound("Documento não encontrado")

    def count_for_process(self, process_id: UUID) -> int:
        return self._s.scalar(
            select(func.count())
            .select_from(DocumentModel)
            .where(DocumentModel.process_id == process_id)
        )

    def count_uploads_by_user_since(self, user_id: UUID, since: datetime) -> int:
        return self._s.scalar(
            select(func.count())
            .select_from(DocumentModel)
            .where(DocumentModel.uploaded_by == user_id, DocumentModel.uploaded_at >= since)
        )


class SqlExtractionRepository:
    def __init__(self, session: Session):
        self._s = session

    def add_run(self, run: ExtractionRun) -> None:
        values = dict(
            id=run.id,
            document_id=run.document_id,
            status=run.status,
            model=run.model,
            duration_ms=run.duration_ms,
            raw_json=run.raw_json,
            warnings=list(run.warnings),
        )
        if run.created_at is not None:
            values["created_at"] = run.created_at
        self._s.execute(insert(ExtractionRunModel).values(**values))

    def mark_run_status(self, run_id: UUID, status: RunStatus) -> None:
        rowcount = self._s.execute(
            update(ExtractionRunModel).where(ExtractionRunModel.id == run_id).values(status=status)
        ).rowcount
        if rowcount == 0:
            raise NotFound("Execução não encontrada")

    def list_runs(self, document_id: UUID) -> Sequence[ExtractionRun]:
        models = self._s.scalars(
            select(ExtractionRunModel)
            .where(ExtractionRunModel.document_id == document_id)
            .order_by(ExtractionRunModel.created_at, ExtractionRunModel.id)
        ).all()
        return [
            ExtractionRun(
                id=m.id,
                document_id=m.document_id,
                model=m.model,
                duration_ms=m.duration_ms,
                raw_json=m.raw_json,
                warnings=tuple(m.warnings),
                status=m.status,
                created_at=m.created_at,
            )
            for m in models
        ]

    def replace_pages(self, document_id: UUID, pages: Sequence[PageText]) -> None:
        self._s.execute(
            delete(DocumentPageModel).where(DocumentPageModel.document_id == document_id)
        )
        for page in pages:
            self._s.execute(
                insert(DocumentPageModel).values(
                    id=uuid.uuid4(),
                    document_id=document_id,
                    run_id=page.run_id,
                    page_number=page.page_number,
                    method=page.method,
                    char_count=page.char_count,
                    ocr_confidence=page.ocr_confidence,
                    text=page.text,
                )
            )

    def list_pages(self, document_id: UUID) -> Sequence[PageText]:
        models = self._s.scalars(
            select(DocumentPageModel)
            .where(DocumentPageModel.document_id == document_id)
            .order_by(DocumentPageModel.page_number)
        ).all()
        return [
            PageText(
                document_id=m.document_id,
                run_id=m.run_id,
                page_number=m.page_number,
                method=m.method,
                char_count=m.char_count,
                ocr_confidence=m.ocr_confidence,
                text=m.text,
            )
            for m in models
        ]


_ACTIVE_JOB = (JobStatus.PENDENTE, JobStatus.PROCESSANDO)


class SqlJobRepository:
    def __init__(self, session: Session):
        self._s = session

    @staticmethod
    def _to_entity(m: ProcessingJobModel) -> ProcessingJob:
        return ProcessingJob(
            id=m.id,
            document_id=m.document_id,
            status=m.status,
            attempts=m.attempts,
            created_at=m.created_at,
            started_at=m.started_at,
            finished_at=m.finished_at,
            error_code=m.error_code,
        )

    def add(self, job: ProcessingJob) -> None:
        values = dict(
            id=job.id,
            document_id=job.document_id,
            status=job.status,
            attempts=job.attempts,
            started_at=job.started_at,
            finished_at=job.finished_at,
            error_code=job.error_code,
        )
        if job.created_at is not None:
            values["created_at"] = job.created_at
        try:
            with self._s.begin_nested():
                self._s.execute(insert(ProcessingJobModel).values(**values))
        except IntegrityError as exc:
            if _is_unique_violation(exc):
                raise Conflict("O documento já tem uma tarefa de processamento ativa") from None
            raise

    def get(self, job_id: UUID) -> ProcessingJob | None:
        m = self._s.get(ProcessingJobModel, job_id, populate_existing=True)
        return self._to_entity(m) if m else None

    def claim_next(self, now: datetime) -> ProcessingJob | None:
        m = self._s.scalars(
            select(ProcessingJobModel)
            .where(ProcessingJobModel.status == JobStatus.PENDENTE)
            .order_by(ProcessingJobModel.created_at, ProcessingJobModel.id)
            .limit(1)
            .with_for_update(skip_locked=True)
        ).first()
        if m is None:
            return None
        m.status = JobStatus.PROCESSANDO
        m.attempts += 1
        m.started_at = now
        m.finished_at = None
        m.error_code = None
        self._s.flush()
        return self._to_entity(m)

    def finish(
        self, job_id: UUID, status: JobStatus, now: datetime, error_code: str | None = None
    ) -> None:
        rowcount = self._s.execute(
            update(ProcessingJobModel)
            .where(ProcessingJobModel.id == job_id)
            .values(status=status, finished_at=now, error_code=error_code)
        ).rowcount
        if rowcount == 0:
            raise NotFound("Tarefa não encontrada")

    def recover_stuck(self, max_attempts: int = DEFAULT_MAX_JOB_ATTEMPTS) -> int:
        return self._s.execute(
            update(ProcessingJobModel)
            .where(
                ProcessingJobModel.status == JobStatus.PROCESSANDO,
                ProcessingJobModel.attempts < max_attempts,
            )
            .values(status=JobStatus.PENDENTE, started_at=None)
        ).rowcount

    def exhaust_stuck(self, max_attempts: int, now: datetime) -> list[ProcessingJob]:
        rows = self._s.scalars(
            update(ProcessingJobModel)
            .where(
                ProcessingJobModel.status == JobStatus.PROCESSANDO,
                ProcessingJobModel.attempts >= max_attempts,
            )
            .values(status=JobStatus.FALHOU, finished_at=now, error_code=EXHAUSTED_CODE)
            .returning(ProcessingJobModel)
        ).all()
        return [self._to_entity(m) for m in rows]

    def active_for_document(self, document_id: UUID) -> ProcessingJob | None:
        m = self._s.scalars(
            select(ProcessingJobModel).where(
                ProcessingJobModel.document_id == document_id,
                ProcessingJobModel.status.in_(_ACTIVE_JOB),
            )
        ).first()
        return self._to_entity(m) if m else None


class SqlEvidenceRepository:
    def __init__(self, session: Session):
        self._s = session

    @staticmethod
    def _to_entity(m: ActivityEvidenceModel) -> ActivityEvidence:
        return ActivityEvidence(
            id=m.id,
            activity_id=m.activity_id,
            document_id=m.document_id,
            page_number=m.page_number,
            excerpt=m.excerpt,
            created_by=m.created_by,
            run_id=m.run_id,
            created_at=m.created_at,
        )

    def add(self, evidence: ActivityEvidence) -> None:
        values = dict(
            id=evidence.id,
            activity_id=evidence.activity_id,
            document_id=evidence.document_id,
            page_number=evidence.page_number,
            excerpt=evidence.excerpt,
            run_id=evidence.run_id,
            created_by=evidence.created_by,
        )
        if evidence.created_at is not None:
            values["created_at"] = evidence.created_at
        _insert(self._s, ActivityEvidenceModel.__table__, values, "Vínculo")

    def remove(self, evidence_id: UUID) -> None:
        rowcount = self._s.execute(
            delete(ActivityEvidenceModel).where(ActivityEvidenceModel.id == evidence_id)
        ).rowcount
        if rowcount == 0:
            raise NotFound("Vínculo não encontrado")

    def list_for_activity(self, activity_id: UUID) -> Sequence[ActivityEvidence]:
        models = self._s.scalars(
            select(ActivityEvidenceModel)
            .where(ActivityEvidenceModel.activity_id == activity_id)
            .order_by(ActivityEvidenceModel.created_at, ActivityEvidenceModel.id)
        ).all()
        return [self._to_entity(m) for m in models]

    def list_for_document(self, document_id: UUID) -> Sequence[ActivityEvidence]:
        models = self._s.scalars(
            select(ActivityEvidenceModel)
            .where(ActivityEvidenceModel.document_id == document_id)
            .order_by(ActivityEvidenceModel.created_at, ActivityEvidenceModel.id)
        ).all()
        return [self._to_entity(m) for m in models]

    def counts_for_activities(self, activity_ids: Sequence[UUID]) -> dict[UUID, int]:
        if not activity_ids:
            return {}
        rows = self._s.execute(
            select(ActivityEvidenceModel.activity_id, func.count())
            .where(ActivityEvidenceModel.activity_id.in_(activity_ids))
            .group_by(ActivityEvidenceModel.activity_id)
        ).all()
        counts = {activity_id: 0 for activity_id in activity_ids}
        counts.update({activity_id: count for activity_id, count in rows})
        return counts


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
        self.documents = SqlDocumentRepository(self._session)
        self.extractions = SqlExtractionRepository(self._session)
        self.jobs = SqlJobRepository(self._session)
        self.evidences = SqlEvidenceRepository(self._session)
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
