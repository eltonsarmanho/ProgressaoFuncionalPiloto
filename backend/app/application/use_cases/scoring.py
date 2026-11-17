"""Scoring use cases for a process: table choice, activities and calculation.

Access follows the process (AccessPolicy): anything outside it is NotFound, never Forbidden.
"""

import re
import uuid
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass, fields, replace
from datetime import date
from decimal import Decimal
from uuid import UUID

from app.application.services.access_policy import AccessPolicy
from app.application.services.audit_service import AuditService
from app.domain.entities.activity import (
    Activity,
    ActivitySource,
    ActivityStatus,
    Candidate,
    Level,
    PeriodPrecision,
    group1_item,
    initial_status,
)
from app.domain.entities.audit import AuditAction
from app.domain.entities.career import select_version
from app.domain.entities.process import FunctionalProcess
from app.domain.entities.professor import Professor
from app.domain.entities.scoring import ScoringMode, ScoringTableVersion
from app.domain.entities.user import User
from app.domain.errors import Conflict, NotFound, StaleVersion, ValidationFailed
from app.domain.repositories.ports import UnitOfWork
from app.domain.rules.interstice import Interstice
from app.domain.rules.process_verification import Alert
from app.domain.rules.scoring_alerts import NotScoredReason
from app.domain.rules.scoring_engine import (
    GROUPS,
    ZERO,
    Counters,
    RowStatus,
    ScoringResult,
    ScoringRow,
    calculate,
    has_evidence,
    is_pit_criterion,
)
from app.domain.rules.scoring_table_choice import verify_table_choice
from app.domain.rules.scoring_verification import (
    MinimumComparison,
    MinimumStatus,
    ScoringContext,
    reference_minimum,
    verify_scoring,
)

PROCESS_ENTITY = "process"
NOT_FOUND = "Processo não encontrado"


@dataclass(frozen=True)
class TableRef:
    table_name: str
    version: ScoringTableVersion


@dataclass(frozen=True)
class TableSuggestion:
    """Chosen version (if any), the suggestion for the professor's unit and table alerts."""

    chosen: TableRef | None
    suggested: TableRef | None
    alerts: list[Alert]


class _ScoringUseCase:
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        audit: AuditService,
        policy: AccessPolicy,
    ):
        self._uow_factory = uow_factory
        self._audit = audit
        self._policy = policy

    def _readable(self, uow: UnitOfWork, actor: User, process_id: UUID) -> FunctionalProcess:
        process = uow.processes.get(process_id)
        if process is None or not self._policy.can_read_process(actor, process):
            raise NotFound(NOT_FOUND)
        return process

    def _writable(self, uow: UnitOfWork, actor: User, process_id: UUID) -> FunctionalProcess:
        process = self._readable(uow, actor, process_id)
        if process.status.is_read_only:
            raise Conflict("Processo concluído ou arquivado não pode ser alterado")
        return process


def _table_ref(uow: UnitOfWork, version: ScoringTableVersion | None) -> TableRef | None:
    if version is None:
        return None
    table = uow.scoring_tables.get_table(version.table_id)
    return TableRef(table.name if table else "", version)


def suggest_version(
    uow: UnitOfWork, professor: Professor, process: FunctionalProcess
) -> ScoringTableVersion | None:
    """Latest version of a table of the professor's unit valid on the interstice end (SEL-02)."""
    candidates = [
        v
        for v in uow.scoring_tables.list_versions_for_unit(professor.unit_id)
        if v.covers(process.end_date)
    ]
    return max(candidates, key=lambda v: v.valid_from, default=None)


def table_alerts(
    uow: UnitOfWork,
    professor: Professor,
    process: FunctionalProcess,
    chosen: ScoringTableVersion | None,
    suggested: ScoringTableVersion | None,
) -> list[Alert]:
    """Alerts about the table of the process (SEL-03, SEL-05..SEL-07)."""
    if chosen is None:
        # Without a choice only the absence of any candidate is worth an alert (SEL-03).
        if suggested is None:
            return verify_table_choice(None, (), professor.unit_id, process.end_date)
        return []
    table = uow.scoring_tables.get_table(chosen.table_id)
    unit_ids = table.unit_ids if table else ()
    return verify_table_choice(chosen, unit_ids, professor.unit_id, process.end_date)


def table_state(uow: UnitOfWork, process: FunctionalProcess) -> TableSuggestion:
    professor = uow.professors.get(process.professor_id)
    chosen = None
    if process.scoring_table_version_id is not None:
        chosen = uow.scoring_tables.get_version(process.scoring_table_version_id)
    suggested = suggest_version(uow, professor, process)
    return TableSuggestion(
        chosen=_table_ref(uow, chosen),
        suggested=_table_ref(uow, suggested),
        alerts=table_alerts(uow, professor, process, chosen, suggested),
    )


class SuggestScoringTable(_ScoringUseCase):
    def execute(self, actor: User, process_id: UUID) -> TableSuggestion:
        """Never writes: the suggestion applies only after the user confirms it (SEL-02)."""
        with self._uow_factory() as uow:
            return table_state(uow, self._readable(uow, actor, process_id))


class ChooseProcessTable(_ScoringUseCase):
    def execute(
        self,
        actor: User,
        process_id: UUID,
        version_id: UUID,
        expected_version: int | None,
        justification: str | None,
    ) -> TableSuggestion:
        with self._uow_factory() as uow:
            process = self._writable(uow, actor, process_id)
            version = uow.scoring_tables.get_version(version_id)
            if version is None:
                raise ValidationFailed("version_id", "Versão de tabela não encontrada")
            professor = uow.professors.get(process.professor_id)
            table = uow.scoring_tables.get_table(version.table_id)
            justification = (justification or "").strip() or None
            if professor.unit_id not in (table.unit_ids if table else ()) and justification is None:
                raise ValidationFailed(
                    "justificativa",
                    "Justificativa obrigatória para tabela de outra unidade acadêmica",
                )
            if expected_version is not None and process.version != expected_version:
                raise StaleVersion("O processo foi alterado por outro usuário; recarregue")
            uow.processes.set_scoring_table_version(process.id, version.id)
            self._audit.record(
                uow,
                actor.id,
                PROCESS_ENTITY,
                process.id,
                AuditAction.UPDATE,
                {"scoring_table_version_id": process.scoring_table_version_id},
                {"scoring_table_version_id": version.id},
                justification,
            )
            uow.commit()
            return table_state(uow, uow.processes.get(process.id))


MAX_VALUE = Decimal(10000)
MAX_TITLE = 300
MAX_EVIDENCE_NOTE = 500
ACADEMIC_PERIOD = re.compile(r"^\d{4}\.\d$")
ACTIVITY_ENTITY = "activity"
ACTIVITY_NOT_FOUND = "Atividade não encontrada"
_ACTIVITY_AUDIT_EXCLUDED = {"id", "process_id", "created_by", "created_at", "updated_at", "version"}
# Changing any of these on an existing activity needs a justification (ATV-08).
JUSTIFIED_FIELDS = (
    "group_number",
    "item_number",
    "quantity",
    "hours",
    "informed_points",
    "points_override",
)


@dataclass(frozen=True)
class ActivityData:
    """What the user informs about an activity; saved exactly as given (CALC and VERIF read it)."""

    title: str
    group_number: int | None = None
    item_number: int | None = None
    description: str = ""
    event_date: date | None = None
    period_start: date | None = None
    period_end: date | None = None
    period_precision: PeriodPrecision = PeriodPrecision.DAY
    academic_period: str | None = None
    level: Level | None = None
    quantity: Decimal | None = None
    hours: Decimal | None = None
    course_hours: Decimal | None = None
    informed_points: Decimal | None = None
    points_override: Decimal | None = None
    evidence_note: str | None = None
    candidates: tuple[Candidate, ...] = ()


def _plain(value):
    if isinstance(value, Decimal):
        return format(value.normalize(), "f")
    return value


def activity_audit_view(activity: Activity) -> dict:
    view = {k: _plain(v) for k, v in asdict(activity).items() if k not in _ACTIVITY_AUDIT_EXCLUDED}
    view["candidates"] = [asdict(c) for c in activity.candidates]
    return view


def _range(field: str, label: str, value: Decimal | None) -> None:
    if value is not None and not 0 <= value <= MAX_VALUE:
        raise ValidationFailed(field, f"{label} deve estar entre 0 e 10000")


def _validate_basics(data: ActivityData, candidates_need_justification: bool = True) -> None:
    if not data.title.strip():
        raise ValidationFailed("title", "Título é obrigatório")
    if len(data.title) > MAX_TITLE:
        raise ValidationFailed("title", "Título deve ter no máximo 300 caracteres")
    if data.evidence_note is not None and len(data.evidence_note) > MAX_EVIDENCE_NOTE:
        raise ValidationFailed(
            "evidence_note", "Nota de comprovante deve ter no máximo 500 caracteres"
        )
    if data.group_number is not None and not 1 <= data.group_number <= 8:
        raise ValidationFailed("group_number", "Grupo deve estar entre I e VIII (1 a 8)")
    if data.item_number is not None and data.item_number < 1:
        raise ValidationFailed("item_number", "Item deve ser um número positivo")
    _range("quantidade", "Quantidade", data.quantity)
    _range("horas", "Horas", data.hours)
    _range("course_hours", "CH da disciplina", data.course_hours)
    _range("informed_points", "Pontos informados", data.informed_points)
    _range("points_override", "Pontos informados", data.points_override)
    if data.period_start and data.period_end and data.period_end < data.period_start:
        raise ValidationFailed("period_end", "Fim do período anterior ao início")
    for candidate in data.candidates:
        if candidates_need_justification and not candidate.justification.strip():
            raise ValidationFailed("candidates", "Item candidato exige justificativa da escolha")


def _apply_group1(data: ActivityData, version: ScoringTableVersion | None) -> ActivityData:
    """Group I needs academic period, level and hours; the item follows the level (ATV-02).

    SPEC_PRECISION: ATV-02 says "the Group I activity" without excepting I.3 (student
    evaluation, a VALOR_INFORMADO criterion that is not a course offering). A criterion of that
    mode chosen explicitly keeps its informed points and skips the course-offering inputs.
    """
    if data.group_number != 1:
        return data
    if version and data.item_number is not None:
        criterion = version.get_criterion(1, data.item_number)
        if criterion is not None and criterion.mode is ScoringMode.VALOR_INFORMADO:
            return data
    if data.academic_period is None or not ACADEMIC_PERIOD.match(data.academic_period):
        raise ValidationFailed("academic_period", "Informe o período letivo no formato AAAA.N")
    if data.level is None:
        raise ValidationFailed("level", "Informe o nível (graduação ou pós-graduação)")
    if data.hours is None:
        raise ValidationFailed("horas", "Informe a CH docente em horas")
    return replace(data, item_number=group1_item(data.level))


def _check_criterion_inputs(data: ActivityData, version: ScoringTableVersion | None) -> None:
    criterion = None
    if version and data.group_number is not None and data.item_number is not None:
        criterion = version.get_criterion(data.group_number, data.item_number)
    if (
        criterion is not None
        and criterion.mode is ScoringMode.POR_UNIDADE
        and data.quantity is not None
        and data.quantity != data.quantity.to_integral_value()
    ):
        raise ValidationFailed("quantidade", "Quantidade deve ser inteira neste critério")
    if (
        data.points_override is not None
        and criterion is not None
        and is_pit_criterion(version, criterion)
    ):
        # SPEC_DEVIATION: refused only where group I is reported in PIT hours (the official
        # table); group I of the old FASI version keeps accepting informed points (PIT-03).
        raise ValidationFailed(
            "points_override",
            "No Grupo I, as horas de PIT são calculadas da carga horária; não há pontos a informar",
        )
    if data.points_override is not None and (
        criterion is None or criterion.mode is not ScoringMode.CARGA_SEMANAL
    ):
        raise ValidationFailed(
            "points_override",
            "Pontos informados só se aplicam a critérios de carga semanal da tabela escolhida",
        )


def normalize_activity(
    data: ActivityData,
    version: ScoringTableVersion | None,
    candidates_need_justification: bool = True,
) -> ActivityData:
    _validate_basics(data, candidates_need_justification)
    data = _apply_group1(replace(data, title=data.title.strip()), version)
    _check_criterion_inputs(data, version)
    return data


class _ActivityUseCase(_ScoringUseCase):
    def _chosen_version(
        self, uow: UnitOfWork, process: FunctionalProcess
    ) -> ScoringTableVersion | None:
        if process.scoring_table_version_id is None:
            return None
        return uow.scoring_tables.get_version(process.scoring_table_version_id)


def _fields(data: ActivityData) -> dict:
    return {f.name: getattr(data, f.name) for f in fields(data)}


class CreateActivity(_ActivityUseCase):
    def execute(
        self,
        actor: User,
        process_id: UUID,
        data: ActivityData,
        justification: str | None = None,
        source: ActivitySource = ActivitySource.MANUAL,
        extraction_run_id: UUID | None = None,
    ) -> Activity:
        """`source` and `extraction_run_id` are not reachable from the public API; the document
        processing passes them (ATV-03, PIPE-09).

        A suggestion may carry candidate items without a justification: the user gives one
        when confirming the choice (CLS-04). A manual entry always needs it.
        """
        with self._uow_factory() as uow:
            process = self._writable(uow, actor, process_id)
            data = normalize_activity(
                data,
                self._chosen_version(uow, process),
                candidates_need_justification=source is ActivitySource.MANUAL,
            )
            justification = (justification or "").strip() or None
            if data.points_override is not None and justification is None:
                raise ValidationFailed(
                    "justificativa", "Justificativa obrigatória ao informar pontos manualmente"
                )
            activity = Activity(
                id=uuid.uuid4(),
                process_id=process.id,
                created_by=actor.id,
                source=source,
                status=initial_status(source),
                extraction_run_id=extraction_run_id,
                **_fields(data),
            )
            uow.activities.add(activity)
            self._audit.record(
                uow,
                actor.id,
                ACTIVITY_ENTITY,
                activity.id,
                AuditAction.CREATE,
                {},
                activity_audit_view(activity),
                justification,
            )
            uow.commit()
            return uow.activities.get(activity.id)


class _ExistingActivityUseCase(_ActivityUseCase):
    def _load(
        self, uow: UnitOfWork, actor: User, activity_id: UUID
    ) -> tuple[Activity, FunctionalProcess]:
        """404 outside access, 409 on a closed process or a stale version (ATV-11..ATV-13)."""
        activity = uow.activities.get(activity_id)
        if activity is None:
            raise NotFound(ACTIVITY_NOT_FOUND)
        process = self._readable(uow, actor, activity.process_id)
        if process.status.is_read_only:
            raise Conflict("Processo concluído ou arquivado não pode ser alterado")
        return activity, process

    @staticmethod
    def _check_version(activity: Activity, expected_version: int) -> None:
        if activity.version != expected_version:
            raise StaleVersion("A atividade foi alterada por outro usuário; recarregue")


def _require_justification(justification: str | None, message: str) -> str:
    justification = (justification or "").strip()
    if not justification:
        raise ValidationFailed("justificativa", message)
    return justification


class UpdateActivity(_ExistingActivityUseCase):
    def execute(
        self,
        actor: User,
        activity_id: UUID,
        data: ActivityData,
        expected_version: int,
        justification: str | None,
    ) -> Activity:
        with self._uow_factory() as uow:
            current, process = self._load(uow, actor, activity_id)
            data = normalize_activity(data, self._chosen_version(uow, process))
            updated = replace(current, **_fields(data))
            if any(getattr(updated, f) != getattr(current, f) for f in JUSTIFIED_FIELDS):
                justification = _require_justification(
                    justification,
                    "Justificativa obrigatória ao alterar item, quantidade, horas ou pontos",
                )
            self._check_version(current, expected_version)
            uow.activities.update(updated, expected_version)
            self._audit.record(
                uow,
                actor.id,
                ACTIVITY_ENTITY,
                activity_id,
                AuditAction.UPDATE,
                activity_audit_view(current),
                activity_audit_view(updated),
                (justification or "").strip() or None,
            )
            uow.commit()
            return uow.activities.get(activity_id)


class ChangeActivityStatus(_ExistingActivityUseCase):
    def execute(
        self,
        actor: User,
        activity_id: UUID,
        target: ActivityStatus,
        expected_version: int,
        justification: str | None,
    ) -> Activity:
        """REJEITADA back to AGUARDANDO_REVISAO is simply a new review round (ATV-09)."""
        with self._uow_factory() as uow:
            current, _ = self._load(uow, actor, activity_id)
            justification = _require_justification(
                justification, "Justificativa obrigatória para mudar o status da atividade"
            )
            if target is current.status:
                raise ValidationFailed("status", "A atividade já está neste status")
            self._check_version(current, expected_version)
            updated = replace(current, status=target)
            uow.activities.update(updated, expected_version)
            self._audit.record(
                uow,
                actor.id,
                ACTIVITY_ENTITY,
                activity_id,
                AuditAction.STATUS,
                {"status": current.status},
                {"status": target},
                justification,
            )
            uow.commit()
            return uow.activities.get(activity_id)


class BulkValidateActivities(_ActivityUseCase):
    def execute(
        self,
        actor: User,
        process_id: UUID,
        activity_ids: Sequence[UUID],
        justification: str | None,
    ) -> list[Activity]:
        """Validates the selected activities with one justification and one audit event each.

        Every activity must belong to the process, otherwise nothing is validated (REV-04).
        The ones already validated are left alone. A validation only happens here, on an
        explicit call (REV-03).
        """
        with self._uow_factory() as uow:
            self._writable(uow, actor, process_id)
            justification = _require_justification(
                justification, "Justificativa obrigatória para validar as atividades"
            )
            selected = []
            for activity_id in dict.fromkeys(activity_ids):
                activity = uow.activities.get(activity_id)
                if activity is None or activity.process_id != process_id:
                    raise NotFound(ACTIVITY_NOT_FOUND)
                selected.append(activity)
        change = ChangeActivityStatus(self._uow_factory, self._audit, self._policy)
        return [
            change.execute(actor, a.id, ActivityStatus.VALIDADA, a.version, justification)
            if a.status is not ActivityStatus.VALIDADA
            else a
            for a in selected
        ]


class MarkActivitiesDistinct(_ExistingActivityUseCase):
    def execute(
        self, actor: User, activity_id: UUID, expected_version: int, justification: str | None
    ) -> Activity:
        """Registers why this activity is not a duplicate of an earlier one (VERIF-06)."""
        with self._uow_factory() as uow:
            current, _ = self._load(uow, actor, activity_id)
            justification = _require_justification(
                justification, "Justificativa obrigatória para marcar a atividade como distinta"
            )
            self._check_version(current, expected_version)
            updated = replace(current, distinct_justification=justification)
            uow.activities.update(updated, expected_version)
            self._audit.record(
                uow,
                actor.id,
                ACTIVITY_ENTITY,
                activity_id,
                AuditAction.UPDATE,
                {"distinct_justification": current.distinct_justification},
                {"distinct_justification": justification},
                justification,
            )
            uow.commit()
            return uow.activities.get(activity_id)


def _listing_order(activity: Activity):
    day = activity.event_date or activity.period_start or activity.period_end
    return (
        activity.group_number is None,
        activity.group_number or 0,
        activity.item_number is None,
        activity.item_number or 0,
        day is None,
        day or date.min,
        activity.created_at is None,
        activity.created_at,
    )


class ListActivities(_ScoringUseCase):
    def execute(
        self,
        actor: User,
        process_id: UUID,
        group_number: int | None = None,
        status: ActivityStatus | None = None,
    ) -> list[Activity]:
        """All activities of the process by group, item and date; unclassified ones last."""
        with self._uow_factory() as uow:
            self._readable(uow, actor, process_id)
            found = uow.activities.list_for_process(process_id, group_number, status)
            return sorted(found, key=_listing_order)


@dataclass(frozen=True)
class ProcessScore:
    """Engine result plus process-level alerts and the comparison with the reference minimum."""

    process_id: UUID
    chosen: TableRef | None
    suggested: TableRef | None
    result: ScoringResult
    activities: tuple[Activity, ...]
    alerts: list[Alert]
    minimum: MinimumComparison


def _without_table(activities: list[Activity], evidence_counts: dict[UUID, int]) -> ScoringResult:
    """No table chosen: total 0 and every activity not scored with reason SEM_TABELA."""
    rows = tuple(
        ScoringRow(
            activity_id=a.id,
            group_number=a.group_number,
            item_number=a.item_number,
            unit_points=None,
            effective_quantity=None,
            formula_text="",
            points=ZERO,
            status=RowStatus.NAO_PONTUADA,
            reasons=(NotScoredReason.SEM_TABELA,),
            evidence_count=evidence_counts.get(a.id, 0),
        )
        for a in activities
    )
    counters = Counters(
        activities=len(activities),
        with_evidence=sum(1 for a in activities if has_evidence(a, evidence_counts.get(a.id, 0))),
        pending=sum(1 for a in activities if a.status is ActivityStatus.AGUARDANDO_REVISAO),
        not_scored=len(activities),
        with_alerts=0,
    )
    return ScoringResult(
        rows, {number: ZERO for number in GROUPS}, ZERO, ZERO, None, counters, ()
    )


class CalculateProcessScore(_ScoringUseCase):
    def execute(self, actor: User, process_id: UUID) -> ProcessScore:
        """Computed on demand from the current data, never stored (AD-006)."""
        with self._uow_factory() as uow:
            process = self._readable(uow, actor, process_id)
            state = table_state(uow, process)
            activities = sorted(uow.activities.list_for_process(process.id), key=_listing_order)
            evidence_counts = uow.evidences.counts_for_activities([a.id for a in activities])
            if state.chosen is None:
                no_table = MinimumComparison(MinimumStatus.NAO_DEFINIDO, None, ZERO)
                return ProcessScore(
                    process.id,
                    None,
                    state.suggested,
                    _without_table(activities, evidence_counts),
                    tuple(activities),
                    state.alerts,
                    no_table,
                )
            version = state.chosen.version
            interstice = Interstice(process.start_date, process.end_date)
            result = calculate(version, activities, interstice, evidence_counts)
            professor = uow.professors.get(process.professor_id)
            code = uow.career_versions.structure_code(professor.career_structure_id)
            versions = uow.career_versions.list_versions(code) if code else []
            career = select_version(versions, process.end_date)
            context = ScoringContext(professor.work_regime, process.current_class, career, version)
            return ProcessScore(
                process.id,
                state.chosen,
                state.suggested,
                result,
                tuple(activities),
                state.alerts + verify_scoring(context, result),
                reference_minimum(version, process.current_class, career, result.total),
            )


class GetActivity(_ScoringUseCase):
    def execute(self, actor: User, activity_id: UUID) -> Activity:
        with self._uow_factory() as uow:
            activity = uow.activities.get(activity_id)
            if activity is None:
                raise NotFound(ACTIVITY_NOT_FOUND)
            self._readable(uow, actor, activity.process_id)
            return activity
