"""Scoring use cases for a process: table choice, activities and calculation.

Access follows the process (AccessPolicy): anything outside it is NotFound, never Forbidden.
"""

import uuid
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass, fields, replace
from datetime import date
from decimal import Decimal
from uuid import UUID

from app.application.services.access_policy import AccessPolicy
from app.application.services.activity_merge import MergeDuplicateActivities
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
from app.domain.entities.scoring import (
    ScoringMode,
    ScoringTableVersion,
    is_group1_load_criterion,
)
from app.domain.entities.user import User
from app.domain.errors import Conflict, NotFound, StaleVersion, ValidationFailed
from app.domain.repositories.ports import UnitOfWork
from app.domain.rules.activity_validity import InvalidReason, Validity, classify_activity
from app.domain.rules.interstice import Interstice
from app.domain.rules.process_verification import Alert
from app.domain.rules.scoring_alerts import NotScoredReason
from app.domain.rules.scoring_duplicates import find_duplicates
from app.domain.rules.scoring_engine import (
    GROUPS,
    ZERO,
    Counters,
    RowStatus,
    ScoringResult,
    ScoringRow,
    calculate,
    has_evidence,
)
from app.domain.rules.scoring_periods import (
    ACADEMIC_PERIOD,
    PeriodState,
    evaluate_period,
    is_yearly_unit,
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
    """Latest version of a table of the professor's unit valid on the interstice end (SEL-02).

    A superseded version is never suggested, even with the same start as its replacement (GI-07).
    """
    candidates = [
        v
        for v in uow.scoring_tables.list_versions_for_unit(professor.unit_id)
        if v.covers(process.end_date) and not v.is_superseded
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
            if version.is_superseded:
                raise ValidationFailed(
                    "version_id",
                    "Esta versão da tabela foi substituída; use a versão atual",
                    code="VERSAO_SUBSTITUIDA",
                )
            # A table of another unit needs no justification (UIM-18); the alert stays.
            justification = (justification or "").strip() or None
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
ACTIVITY_ENTITY = "activity"
ACTIVITY_NOT_FOUND = "Atividade não encontrada"
DISTINCT_DEFAULT_TEXT = "Marcada como distinta pelo usuário"
_ACTIVITY_AUDIT_EXCLUDED = {"id", "process_id", "created_by", "created_at", "updated_at", "version"}


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
    unit_points_override: Decimal | None = None
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


def _validate_basics(data: ActivityData) -> None:
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
    _range("points_override", "Pontuação manual", data.points_override)
    _range("unit_points_override", "Valor unitário", data.unit_points_override)
    if data.period_start and data.period_end and data.period_end < data.period_start:
        raise ValidationFailed("period_end", "Fim do período anterior ao início")


def _apply_group1(data: ActivityData) -> ActivityData:
    """Group I needs academic period, level and hours; the item follows the level (ATV-02)."""
    if data.group_number != 1:
        return data
    if data.academic_period is None or not ACADEMIC_PERIOD.fullmatch(data.academic_period):
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
        and is_group1_load_criterion(criterion)
    ):
        # PIT-03, GI-05: group I hours come from the weekly load in every table version, whether
        # the group is outside the total or counts in it.
        raise ValidationFailed(
            "points_override",
            "No Grupo I, as horas de PIT são calculadas da carga horária; não há pontos a informar",
        )
    if data.unit_points_override is not None and (
        criterion is None
        or criterion.mode not in (ScoringMode.POR_UNIDADE, ScoringMode.POR_BLOCO_DE_HORAS)
    ):
        raise ValidationFailed(
            "unit_points_override",
            "O valor unitário manual só se aplica a itens por unidade ou por bloco de horas",
        )
    if data.points_override is not None and (
        criterion is None or criterion.mode is not ScoringMode.CARGA_SEMANAL
    ):
        raise ValidationFailed(
            "points_override",
            "Esta tabela não aceita pontuação manual neste item; nos itens por unidade ou por "
            "bloco de horas, informe o valor unitário",
        )


def normalize_activity(data: ActivityData, version: ScoringTableVersion | None) -> ActivityData:
    _validate_basics(data)
    data = _apply_group1(replace(data, title=data.title.strip()))
    _check_criterion_inputs(data, version)
    return data


class _ActivityUseCase(_ScoringUseCase):
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        audit: AuditService,
        policy: AccessPolicy,
        merger: MergeDuplicateActivities | None = None,
    ):
        super().__init__(uow_factory, audit, policy)
        self._merger = merger or MergeDuplicateActivities(audit)

    def _chosen_version(
        self, uow: UnitOfWork, process: FunctionalProcess
    ) -> ScoringTableVersion | None:
        if process.scoring_table_version_id is None:
            return None
        return uow.scoring_tables.get_version(process.scoring_table_version_id)


NEEDS_CATEGORY_MESSAGE = "Escolha a categoria antes de validar"
NOT_VALID_CODE = "ATIVIDADE_NAO_VALIDA"
NO_CATEGORY = "SEM_CATEGORIA"  # the `reason` of a skipped activity that has no category


def _day(value: date | None) -> str:
    return value.strftime("%d/%m/%Y") if value else ""


def _not_valid_message(validity: Validity) -> str:
    """Why the activity cannot be validated, in words for the person (VAL-06)."""
    params = validity.params
    match validity.reason:
        case InvalidReason.REJEITADA:
            return "A atividade foi rejeitada; reabra-a antes de validar"
        case InvalidReason.FORA_DO_INTERSTICIO:
            return (
                "A atividade está fora do interstício "
                f"({_day(params['interstice_start'])} a {_day(params['interstice_end'])})"
            )
        case InvalidReason.CARGA_HORARIA_INSUFICIENTE:
            return (
                f"Carga horária insuficiente: {params['hours'].normalize():f} h; "
                f"o item exige {params['min_hours'].normalize():f} h"
            )
        case InvalidReason.GRUPO_NAO_CONTA:
            return "O grupo da atividade não conta na pontuação"
        case _:
            return "A atividade é duplicada de outra"


def _classifier(uow: UnitOfWork, process: FunctionalProcess) -> Callable[[Activity], Validity]:
    """The validity of an activity of the process, as the engine decides it (AD-006: computed
    on demand, never stored). The duplicates are looked up once for all the calls."""
    version = None
    if process.scoring_table_version_id is not None:
        version = uow.scoring_tables.get_version(process.scoring_table_version_id)
    interstice = Interstice(process.start_date, process.end_date)
    duplicates: set[UUID] = set()
    if version is not None:
        activities = uow.activities.list_for_process(process.id)
        contents = uow.evidences.content_keys_for_activities([a.id for a in activities])
        duplicates = find_duplicates(activities, contents)
    return lambda activity: classify_activity(activity, version, interstice, duplicates)


def _skip_reason(validity: Validity) -> str | None:
    """Why an activity cannot be validated, or None when it can: the reason of the validity, or
    `SEM_CATEGORIA`."""
    if not validity.is_valid:
        return validity.reason.value
    return NO_CATEGORY if validity.needs_category else None


def _check_inside_interstice(
    activity: Activity, version: ScoringTableVersion | None, process: FunctionalProcess
) -> None:
    """The date of an activity edited by hand has to touch the interstice (EDT-02, EDT-03).

    An item measured by year only needs the period to cross it. An activity with no date, or an
    interstice that cannot be checked, passes. Not used for an activity read from a document: that
    one is created as it was read and shows up as not valid (SEC-06).
    """
    interstice = Interstice(process.start_date, process.end_date)
    criterion = None
    if version is not None and activity.group_number and activity.item_number:
        criterion = version.get_criterion(activity.group_number, activity.item_number)
    yearly = criterion is not None and is_yearly_unit(criterion.unit_label)
    if evaluate_period(activity, interstice, yearly) is not PeriodState.FORA:
        return
    if activity.event_date is not None:
        field = "event_date"
    elif activity.period_start and activity.period_start > interstice.end:
        field = "period_start"
    else:
        field = "period_end" if activity.period_end else "period_start"
    raise ValidationFailed(
        field, f"A data deve estar entre {_day(interstice.start)} e {_day(interstice.end)}"
    )


_DATE_FIELDS = ("event_date", "period_start", "period_end", "period_precision")


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

        The justification is optional everywhere (UIM-16): audited when sent, never required.
        """
        with self._uow_factory() as uow:
            process = self._writable(uow, actor, process_id)
            data = normalize_activity(data, self._chosen_version(uow, process))
            justification = (justification or "").strip() or None
            activity = Activity(
                id=uuid.uuid4(),
                process_id=process.id,
                created_by=actor.id,
                source=source,
                status=initial_status(source),
                extraction_run_id=extraction_run_id,
                **_fields(data),
            )
            if source is ActivitySource.MANUAL:
                _check_inside_interstice(activity, self._chosen_version(uow, process), process)
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
            if source is ActivitySource.MANUAL:
                # A reading creates its activities one by one and links each to its page after
                # that: the document processing merges once at the end, so the proof of a
                # duplicate is not left on an activity that was merged before it arrived.
                self._merger.merge_process(uow, process.id, actor.id)
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


def _normalize_for_update(
    data: ActivityData, current: Activity, version: ScoringTableVersion | None
) -> ActivityData:
    """Normalize an edit; a stored manual score the item refuses is cleared, not rejected.

    The edit form resends the stored `points_override` with every other field. When the item no
    longer accepts it (a value kept from an older table or item), the same value coming back is
    dropped, and the UPDATE audit event keeps the previous one (CAEDI-01). A different value
    that the item refuses is still a 422 (CAEDI-02).
    """
    try:
        return normalize_activity(data, version)
    except ValidationFailed as refusal:
        if refusal.field != "points_override" or data.points_override != current.points_override:
            raise
    return normalize_activity(replace(data, points_override=None), version)


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
            version = self._chosen_version(uow, process)
            data = _normalize_for_update(data, current, version)
            updated = replace(current, **_fields(data))
            self._check_version(current, expected_version)
            # A date that stays as it was is not judged again: only the one the body brings.
            if any(getattr(updated, f) != getattr(current, f) for f in _DATE_FIELDS):
                _check_inside_interstice(updated, version, process)
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
            # DUP-04: what was merged before stays merged, even if this edit made them differ
            self._merger.merge_process(uow, process.id, actor.id)
            uow.commit()
            return uow.activities.get(activity_id)


class ChangeActivityStatus(_ExistingActivityUseCase):
    @staticmethod
    def _check_can_validate(
        uow: UnitOfWork, process: FunctionalProcess, activity: Activity
    ) -> None:
        """Only a valid activity with a category is validated (VAL-03, VAL-06)."""
        validity = _classifier(uow, process)(activity)
        if not validity.is_valid:
            raise ValidationFailed("status", _not_valid_message(validity), NOT_VALID_CODE)
        if validity.needs_category:
            raise ValidationFailed("categoria", NEEDS_CATEGORY_MESSAGE)

    def execute(
        self,
        actor: User,
        activity_id: UUID,
        target: ActivityStatus,
        expected_version: int,
        justification: str | None,
    ) -> Activity:
        """REJEITADA back to AGUARDANDO_REVISAO is simply a new review round (ATV-09).

        The justification is optional (UIM-14): audited when sent, never required.
        """
        with self._uow_factory() as uow:
            current, process = self._load(uow, actor, activity_id)
            justification = (justification or "").strip() or None
            if target is current.status:
                raise ValidationFailed("status", "A atividade já está neste status")
            self._check_version(current, expected_version)
            if target is ActivityStatus.VALIDADA:
                self._check_can_validate(uow, process, current)
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


@dataclass(frozen=True)
class SkippedActivity:
    """An activity the batch left as it was: `reason` is `SEM_CATEGORIA` or the reason of the
    validity (`FORA_DO_INTERSTICIO`, `REJEITADA`, ...)."""

    id: UUID
    reason: str


@dataclass(frozen=True)
class BulkValidation:
    """`activities` are the selected ones that are validated now; `skipped` the ones left out."""

    activities: list[Activity]
    skipped: list[SkippedActivity]


class BulkValidateActivities(_ActivityUseCase):
    def execute(
        self,
        actor: User,
        process_id: UUID,
        activity_ids: Sequence[UUID],
        justification: str | None,
    ) -> BulkValidation:
        """Validates the selected activities with one audit event each (UIM-14).

        The justification is optional; when sent, it goes into every event.

        The ones that cannot be validated (no category, or not valid) are not validated and come
        back in `skipped` with the reason (VAL-04). An activity of another process (404) or a
        version changed by someone else (409) anywhere in the list validates none, all in one
        unit of work (REV-04, VER-09). The ones already validated are left alone. A validation
        only happens here, on an explicit call (REV-03).
        """
        with self._uow_factory() as uow:
            process = self._writable(uow, actor, process_id)
            justification = (justification or "").strip() or None
            selected = []
            for activity_id in dict.fromkeys(activity_ids):
                activity = uow.activities.get(activity_id)
                if activity is None or activity.process_id != process_id:
                    raise NotFound(ACTIVITY_NOT_FOUND)
                selected.append(activity)
            classify = _classifier(uow, process)
            validated: list[Activity] = []
            skipped: list[SkippedActivity] = []
            for current in selected:
                if current.status is not ActivityStatus.VALIDADA:
                    reason = _skip_reason(classify(current))
                    if reason is not None:
                        skipped.append(SkippedActivity(current.id, reason))
                        continue
                    uow.activities.update(
                        replace(current, status=ActivityStatus.VALIDADA), current.version
                    )
                    self._audit.record(
                        uow,
                        actor.id,
                        ACTIVITY_ENTITY,
                        current.id,
                        AuditAction.STATUS,
                        {"status": current.status},
                        {"status": ActivityStatus.VALIDADA},
                        justification,
                    )
                validated.append(current)
            uow.commit()
            return BulkValidation([uow.activities.get(a.id) for a in validated], skipped)


class MarkActivitiesDistinct(_ExistingActivityUseCase):
    def execute(
        self, actor: User, activity_id: UUID, expected_version: int, justification: str | None
    ) -> Activity:
        """Registers why this activity is not a duplicate of an earlier one (VERIF-06)."""
        with self._uow_factory() as uow:
            current, _ = self._load(uow, actor, activity_id)
            justification = (justification or "").strip() or None
            self._check_version(current, expected_version)
            # The text is what marks the activity as distinct (the duplicate rule reads it),
            # so a mark without one stores a neutral default (UIM-14).
            updated = replace(
                current, distinct_justification=justification or DISTINCT_DEFAULT_TEXT
            )
            uow.activities.update(updated, expected_version)
            self._audit.record(
                uow,
                actor.id,
                ACTIVITY_ENTITY,
                activity_id,
                AuditAction.UPDATE,
                {"distinct_justification": current.distinct_justification},
                {"distinct_justification": updated.distinct_justification},
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


@dataclass(frozen=True)
class ActivityListing:
    """The activities of a process as the Etapa 3 shows them (SEC-02, SEC-06..SEC-09).

    `activities` are the ones to list, without the merged ones. The maps are by activity id:
    `validity` (of the whole process, whatever the filters), `merged` (the duplicates merged into
    an activity, only for the ones that have any) and `predicted_points` (what the activity
    scores or would score once validated; absent when it has no category, is not valid, belongs
    to the group outside the total or the process has no table).
    """

    activities: list[Activity]
    validity: dict[UUID, Validity]
    merged: dict[UUID, list[Activity]]
    predicted_points: dict[UUID, Decimal]


def _describe_process(uow: UnitOfWork, process: FunctionalProcess) -> ActivityListing:
    """Everything of the process in one calculation: validity, merged ones and the prediction."""
    score = compute_process_score(uow, process)
    merged: dict[UUID, list[Activity]] = {}
    for activity in uow.activities.list_for_process(process.id, include_merged=True):
        if activity.merged_into_id is not None:
            merged.setdefault(activity.merged_into_id, []).append(activity)
    predicted = {
        row.activity_id: row.points
        for row in score.result.rows
        if row.status in (RowStatus.PONTUADA, RowStatus.POTENCIAL) and not row.outside_total
    }
    return ActivityListing(list(score.activities), score.result.validity, merged, predicted)


class ListActivities(_ScoringUseCase):
    def execute(
        self,
        actor: User,
        process_id: UUID,
        group_number: int | None = None,
        status: ActivityStatus | None = None,
    ) -> ActivityListing:
        """All activities of the process by group, item and date; unclassified ones last.

        The merged activities are not listed; each kept one carries them. The validity is the one
        of the engine (AD-006: computed on demand), so a corrected activity comes back valid.
        """
        with self._uow_factory() as uow:
            process = self._readable(uow, actor, process_id)
            described = _describe_process(uow, process)
            kept = [
                a
                for a in described.activities
                if (group_number is None or a.group_number == group_number)
                and (status is None or a.status is status)
            ]
            return replace(described, activities=kept)


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


def _without_table(
    activities: list[Activity], evidence_counts: dict[UUID, int], interstice: Interstice
) -> ScoringResult:
    """No table chosen: total 0 and every valid activity not scored with reason SEM_TABELA.

    The activities that are not valid (rejected, outside the interstice) do not enter either; the
    validity without a table leaves out what depends on it (hours, group, duplicates) (SEG-04).
    """
    validity = {a.id: classify_activity(a, None, interstice, set()) for a in activities}
    valid = [a for a in activities if validity[a.id].is_valid]
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
        for a in valid
    )
    counters = Counters(
        activities=len(valid),
        with_evidence=sum(1 for a in valid if has_evidence(a, evidence_counts.get(a.id, 0))),
        pending=sum(1 for a in valid if a.status is ActivityStatus.AGUARDANDO_REVISAO),
        not_scored=len(valid),
        with_alerts=0,
    )
    return ScoringResult(
        rows, {number: ZERO for number in GROUPS}, ZERO, ZERO, None, counters, (),
        validity=validity,
    )  # fmt: skip


def compute_process_score(uow: UnitOfWork, process: FunctionalProcess) -> ProcessScore:
    """Computed on demand from the current data, never stored (AD-006).

    Takes no actor: the caller checks access first (the screen use case) or runs on behalf of a
    job whose request was already authorized (document generation).
    """
    state = table_state(uow, process)
    activities = sorted(uow.activities.list_for_process(process.id), key=_listing_order)
    ids = [a.id for a in activities]
    evidence_counts = uow.evidences.counts_for_activities(ids)
    contents = uow.evidences.content_keys_for_activities(ids)
    if state.chosen is None:
        no_table = MinimumComparison(MinimumStatus.NAO_DEFINIDO, None, ZERO)
        return ProcessScore(
            process.id,
            None,
            state.suggested,
            _without_table(
                activities, evidence_counts, Interstice(process.start_date, process.end_date)
            ),
            tuple(activities),
            state.alerts,
            no_table,
        )
    version = state.chosen.version
    interstice = Interstice(process.start_date, process.end_date)
    result = calculate(version, activities, interstice, evidence_counts, contents)
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


class CalculateProcessScore(_ScoringUseCase):
    def execute(self, actor: User, process_id: UUID) -> ProcessScore:
        with self._uow_factory() as uow:
            process = self._readable(uow, actor, process_id)
            return compute_process_score(uow, process)


class GetActivity(_ScoringUseCase):
    def execute(self, actor: User, activity_id: UUID) -> ActivityListing:
        """One activity with the same description as in the list."""
        with self._uow_factory() as uow:
            activity = uow.activities.get(activity_id)
            if activity is None:
                raise NotFound(ACTIVITY_NOT_FOUND)
            process = self._readable(uow, actor, activity.process_id)
            described = _describe_process(uow, process)
            if activity.id in described.validity:
                return replace(
                    described,
                    activities=[a for a in described.activities if a.id == activity.id],
                )
            # a merged activity is not in the list: it is described on its own
            validity = {activity.id: _classifier(uow, process)(activity)}
            return ActivityListing([activity], validity, {}, {})
