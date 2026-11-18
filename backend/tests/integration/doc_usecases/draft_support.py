"""Builders for the tests of the report draft, the wording and the arrangement use cases."""

import dataclasses

from app.application.services.generation_inputs import load_generation_inputs
from app.application.use_cases.report_draft import (
    GetReportDraft,
    SaveReportEntry,
    SaveReportSection,
)
from app.domain.rules.report_draft import propose_draft
from app.infrastructure.documents.config_loader import ReportConfigLoader, load_report_config


def get_draft_uc(world) -> GetReportDraft:
    return GetReportDraft(world.uow_factory, world.audit, world.policy, ReportConfigLoader())


def save_entry_uc(world) -> SaveReportEntry:
    return SaveReportEntry(world.uow_factory, world.audit, world.policy, ReportConfigLoader())


def save_section_uc(world) -> SaveReportSection:
    return SaveReportSection(world.uow_factory, world.audit, world.policy, ReportConfigLoader())


def set_status(world, status):
    """Moves the main process to `status` straight in the database."""
    with world.uow_factory() as uow:
        current = uow.processes.get(world.process.id)
        uow.processes.update(dataclasses.replace(current, status=status), current.version)
        uow.commit()


def proposal(world):
    """The draft the system proposes now for the main process (version 0)."""
    config = load_report_config()
    with world.uow_factory() as uow:
        inputs = load_generation_inputs(uow, uow.processes.get(world.process.id))
    return propose_draft(
        config.template, inputs.activities, config.group_map, process_id=world.process.id
    )


def save_proposal(world):
    """Stores the current proposal as the saved draft (version 1) and returns it."""
    draft = proposal(world)
    with world.uow_factory() as uow:
        saved = uow.report_drafts.create(draft, world.admin.id, 0)
        uow.commit()
    return saved


def stored_draft(world):
    with world.uow_factory() as uow:
        return uow.report_drafts.get(world.process.id)


def entries_by_section(draft) -> dict[str, list]:
    return {s.key: [e.activity_id for e in s.entries] for s in draft.sections if s.entries}
