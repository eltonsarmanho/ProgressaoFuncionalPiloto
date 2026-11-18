"""The report draft: reading it, editing its text, moving an activity, asking for the wording
and running it in the background (REL-01, REL-03 to REL-08, REL-11, REL-13 to REL-15).

Access follows the process (AccessPolicy): anything outside it is NotFound, never Forbidden. Audit
events carry identifiers, states and codes only, never the text of an entry (AD-014).
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from uuid import UUID

from app.application.services.access_policy import AccessPolicy
from app.application.services.audit_service import AuditService
from app.application.services.generation_inputs import GenerationInputs, load_generation_inputs
from app.application.use_cases.generated_documents import _EditUseCase
from app.application.use_cases.scoring import _ScoringUseCase
from app.domain.entities.activity import Activity
from app.domain.entities.audit import AuditAction
from app.domain.entities.generated import GenerationAlert
from app.domain.entities.process import FunctionalProcess
from app.domain.entities.report import DraftEntry, DraftSection, EntrySource, ReportDraft
from app.domain.entities.user import User
from app.domain.errors import NotFound, ValidationFailed
from app.domain.repositories.ports import ReportConfigProvider, UnitOfWork
from app.domain.rules.report_draft import (
    STALE,
    STALE_MESSAGE,
    ReportConfig,
    empty_sections,
    move_entry,
    propose_draft,
    reconcile_draft,
)

DRAFT_ENTITY = "report_draft"
MAX_TEXT_LENGTH = 20_000


@dataclass(frozen=True)
class ReportDraftView:
    """What the screen shows: the draft saved and brought up to date, or the proposal when none
    was saved (`saved` False, version 0); the sections without anything; the alert when the
    activities moved on since the last edit (REL-11)."""

    draft: ReportDraft
    saved: bool
    empty_sections: tuple[str, ...]
    alerts: tuple[GenerationAlert, ...]
    activities: tuple[Activity, ...]
    item_names: Mapping[tuple[int, int], str]


def _item_names(inputs: GenerationInputs) -> dict[tuple[int, int], str]:
    version = inputs.version
    if version is None:
        return {}
    return {
        (c.group_number, c.item_number): c.description
        for group in version.groups
        for c in group.criteria
    }


@dataclass(frozen=True)
class _Current:
    """The draft as the generation sees it now: `draft` is the saved one brought up to date, or
    the proposal; `saved` is the one stored, None when there is none."""

    draft: ReportDraft
    saved: ReportDraft | None
    inputs: GenerationInputs
    config: ReportConfig


def _current(
    uow: UnitOfWork, process: FunctionalProcess, config_provider: ReportConfigProvider
) -> _Current:
    """Reads only; nothing is written."""
    inputs = load_generation_inputs(uow, process)
    config = config_provider.load()
    saved = uow.report_drafts.get(process.id)
    if saved is None:
        draft = propose_draft(
            config.template, inputs.activities, config.group_map, process_id=process.id
        )
    else:
        draft = reconcile_draft(saved, inputs.activities, config.template, config.group_map)
    return _Current(draft, saved, inputs, config)


class GetReportDraft(_ScoringUseCase):
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        audit: AuditService,
        policy: AccessPolicy,
        report_config: ReportConfigProvider,
    ) -> None:
        super().__init__(uow_factory, audit, policy)
        self._report_config = report_config

    def execute(self, actor: User, process_id: UUID) -> ReportDraftView:
        """A read never writes: the first one only proposes (REL-01)."""
        with self._uow_factory() as uow:
            process = self._readable(uow, actor, process_id)
            current = _current(uow, process, self._report_config)
        draft = current.draft
        stale = any(w.code is STALE for section in draft.sections for w in section.warnings)
        return ReportDraftView(
            draft=draft,
            saved=current.saved is not None,
            empty_sections=empty_sections(draft),
            alerts=(GenerationAlert(STALE, STALE_MESSAGE),) if stale else (),
            activities=current.inputs.activities,
            item_names=_item_names(current.inputs),
        )


def _without_stale(sections: tuple[DraftSection, ...]) -> tuple[DraftSection, ...]:
    """The alert is computed at every read; it is never stored."""
    return tuple(
        replace(s, warnings=tuple(w for w in s.warnings if w.code is not STALE)) for s in sections
    )


class _DraftEditUseCase(_EditUseCase):
    """An edit of the draft: made on the draft brought up to date and saved with the version the
    user saw, so an activity that arrived since the last save can be edited too (REL-07)."""

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        audit: AuditService,
        policy: AccessPolicy,
        report_config: ReportConfigProvider,
    ) -> None:
        super().__init__(uow_factory, audit, policy)
        self._report_config = report_config

    def _save(
        self,
        actor: User,
        process_id: UUID,
        expected_version: int,
        operation: str,
        edit: Callable[[ReportDraft, GenerationInputs, ReportConfig], ReportDraft],
        check: Callable[[], None] = lambda: None,
    ) -> ReportDraft:
        """`edit` makes the new draft from the one brought up to date; the first save creates the
        draft and needs `expected_version` 0."""
        with self._uow_factory() as uow:
            process = self._editable(uow, actor, process_id)
            check()
            current = _current(uow, process, self._report_config)
            inputs, config = current.inputs, current.config
            with self._versioned():
                if current.saved is None:
                    draft = edit(current.draft, inputs, config)
                    draft = replace(draft, sections=_without_stale(draft.sections))
                    result = uow.report_drafts.create(draft, actor.id, expected_version)
                else:
                    saved = current.saved

                    def change(sections: tuple[DraftSection, ...]) -> tuple[DraftSection, ...]:
                        now = reconcile_draft(
                            replace(saved, sections=sections),
                            inputs.activities,
                            config.template,
                            config.group_map,
                        )
                        return _without_stale(edit(now, inputs, config).sections)

                    result = uow.report_drafts.edit(process.id, expected_version, change, actor.id)
            created = current.saved is None
            self._audit.record(
                uow,
                actor.id,
                DRAFT_ENTITY,
                process.id,
                AuditAction.CREATE if created else AuditAction.UPDATE,
                {"version": result.version - 1},
                {"version": result.version, "operation": operation},
            )
            uow.commit()
            return result


def _checked_length(text: str, field: str) -> None:
    if len(text) > MAX_TEXT_LENGTH:
        raise ValidationFailed(field, f"O texto passa de {MAX_TEXT_LENGTH} caracteres")


class SaveReportEntry(_DraftEditUseCase):
    def execute(
        self, actor: User, process_id: UUID, activity_id: UUID, text: str, expected_version: int
    ) -> ReportDraft:
        """The text of one activity becomes the user's and the AI never rewrites it (REL-07).
        The first save creates the draft (`expected_version` 0); a version that is not the stored
        one is a 409 `VERSAO_DESATUALIZADA`; more than 20 000 characters is a 422."""

        def edit(draft: ReportDraft, inputs: GenerationInputs, config: ReportConfig):
            found = False
            sections = []
            for section in draft.sections:
                entries = []
                for entry in section.entries:
                    if entry.activity_id == activity_id:
                        found = True
                        entry = DraftEntry(activity_id, text, EntrySource.USUARIO)
                    entries.append(entry)
                sections.append(replace(section, entries=tuple(entries)))
            if not found:
                raise NotFound("Atividade não encontrada no rascunho")
            return replace(draft, sections=tuple(sections))

        return self._save(
            actor,
            process_id,
            expected_version,
            "ENTRY",
            edit,
            check=lambda: _checked_length(text, "text"),
        )


class SaveReportSection(_DraftEditUseCase):
    def execute(
        self, actor: User, process_id: UUID, section_key: str, free_text: str, expected_version: int
    ) -> ReportDraft:
        """The free text of a section (REL-07); same version rule and same limit as an entry."""

        def edit(draft: ReportDraft, inputs: GenerationInputs, config: ReportConfig):
            if all(s.key != section_key for s in draft.sections):
                raise NotFound("Seção não encontrada")
            return replace(
                draft,
                sections=tuple(
                    replace(s, free_text=free_text) if s.key == section_key else s
                    for s in draft.sections
                ),
            )

        return self._save(
            actor,
            process_id,
            expected_version,
            "SECTION",
            edit,
            check=lambda: _checked_length(free_text, "free_text"),
        )


class MoveReportEntry(_DraftEditUseCase):
    def execute(
        self,
        actor: User,
        process_id: UUID,
        activity_id: UUID,
        section_key: str,
        expected_version: int,
    ) -> ReportDraft:
        """The activity goes to the end of the section and the generation uses that choice
        (REL-08). A section the template does not have is a 422; the rest is as in
        SaveReportEntry."""

        def edit(draft: ReportDraft, inputs: GenerationInputs, config: ReportConfig):
            if config.template.section(section_key) is None:
                raise ValidationFailed("section_key", "A seção não existe no modelo do Relatório")
            return move_entry(draft, activity_id, section_key, inputs.activities, config.template)

        return self._save(actor, process_id, expected_version, "MOVE", edit)
