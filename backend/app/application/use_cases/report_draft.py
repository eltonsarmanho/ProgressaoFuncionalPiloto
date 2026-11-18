"""The report draft: reading it, editing its text, moving an activity, asking for the wording
and running it in the background (REL-01, REL-03 to REL-08, REL-11, REL-13 to REL-15).

Access follows the process (AccessPolicy): anything outside it is NotFound, never Forbidden. Audit
events carry identifiers, states and codes only, never the text of an entry (AD-014).
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from uuid import UUID

from app.application.services.access_policy import AccessPolicy
from app.application.services.audit_service import AuditService
from app.application.services.generation_inputs import GenerationInputs, load_generation_inputs
from app.application.use_cases.scoring import _ScoringUseCase
from app.domain.entities.activity import Activity
from app.domain.entities.generated import GenerationAlert
from app.domain.entities.process import FunctionalProcess
from app.domain.entities.report import ReportDraft
from app.domain.entities.user import User
from app.domain.repositories.ports import ReportConfigProvider, UnitOfWork
from app.domain.rules.report_draft import (
    STALE,
    STALE_MESSAGE,
    empty_sections,
    propose_draft,
    reconcile_draft,
)


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


def current_draft(
    uow: UnitOfWork,
    process: FunctionalProcess,
    config_provider: ReportConfigProvider,
) -> tuple[ReportDraft, bool, GenerationInputs]:
    """The draft as the generation sees it now, whether it is saved, and the inputs it used.
    Nothing is written."""
    inputs = load_generation_inputs(uow, process)
    config = config_provider.load()
    saved = uow.report_drafts.get(process.id)
    if saved is None:
        draft = propose_draft(
            config.template, inputs.activities, config.group_map, process_id=process.id
        )
        return draft, False, inputs
    draft = reconcile_draft(saved, inputs.activities, config.template, config.group_map)
    return draft, True, inputs


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
            draft, saved, inputs = current_draft(uow, process, self._report_config)
        stale = any(w.code is STALE for section in draft.sections for w in section.warnings)
        return ReportDraftView(
            draft=draft,
            saved=saved,
            empty_sections=empty_sections(draft),
            alerts=(GenerationAlert(STALE, STALE_MESSAGE),) if stale else (),
            activities=inputs.activities,
            item_names=_item_names(inputs),
        )
