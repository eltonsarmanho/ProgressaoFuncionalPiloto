"""Builders for the tests of the report draft, the wording and the arrangement use cases."""

import dataclasses

from app.application.services.generation_inputs import load_generation_inputs
from app.application.use_cases.comprovante_layout import GetComprovanteLayout, SaveComprovanteLayout
from app.application.use_cases.report_draft import (
    GetReportDraft,
    ListWordingJobs,
    MoveReportEntry,
    RequestSectionWording,
    RunWording,
    SaveReportEntry,
    SaveReportSection,
)
from app.domain.rules.report_draft import propose_draft
from app.infrastructure.documents.config_loader import ReportConfigLoader, load_report_config
from app.infrastructure.documents.front_matter import TOC_CAPACITY


def get_draft_uc(world) -> GetReportDraft:
    return GetReportDraft(world.uow_factory, world.audit, world.policy, ReportConfigLoader())


def save_entry_uc(world) -> SaveReportEntry:
    return SaveReportEntry(world.uow_factory, world.audit, world.policy, ReportConfigLoader())


def save_section_uc(world) -> SaveReportSection:
    return SaveReportSection(world.uow_factory, world.audit, world.policy, ReportConfigLoader())


def move_uc(world) -> MoveReportEntry:
    return MoveReportEntry(world.uow_factory, world.audit, world.policy, ReportConfigLoader())


def request_wording_uc(world, clock) -> RequestSectionWording:
    return RequestSectionWording(
        world.uow_factory, world.audit, world.policy, clock, ReportConfigLoader()
    )


def list_wording_uc(world) -> ListWordingJobs:
    return ListWordingJobs(world.uow_factory, world.audit, world.policy)


def run_wording_uc(world, clock, writer) -> RunWording:
    return RunWording(world.uow_factory, world.audit, clock, ReportConfigLoader(), writer)


class FakeReportWriter:
    """The AI of the tests: answers with the texts it was given by activity id, raises `error`
    when told to, and runs `during` while the call is in flight."""

    def __init__(self, answers=None, error=None, during=None):
        self.answers = answers or {}
        self.error = error
        self.during = during
        self.calls = []

    def draft(self, section_title, items):
        self.calls.append((section_title, list(items)))
        if self.during is not None:
            self.during()
        if self.error is not None:
            raise self.error
        return {
            i.activity_id: self.answers[i.activity_id]
            for i in items
            if i.activity_id in self.answers
        }


def get_layout_uc(world) -> GetComprovanteLayout:
    return GetComprovanteLayout(world.uow_factory, world.audit, world.policy, TOC_CAPACITY)


def save_layout_uc(world) -> SaveComprovanteLayout:
    return SaveComprovanteLayout(world.uow_factory, world.audit, world.policy)


def save_current_layout(world):
    """Stores the arrangement the generation would use now as the saved one (version 1)."""
    with world.uow_factory() as uow:
        layout = load_generation_inputs(uow, uow.processes.get(world.process.id)).layout
        saved = uow.comprovante_layouts.create(layout, world.admin.id, 0)
        uow.commit()
    return saved


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
