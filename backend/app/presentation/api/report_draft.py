"""Report draft routes (REL-03, REL-07, REL-08, REL-13, UIG-02, UIG-08): read the draft, edit the
text of an entry or of a section, move an activity between sections, and ask for the wording of a
section in the background.

Access follows the process: outside it, 404. A read never writes: the first one only proposes. The
first save uses `expected_version` 0; a version that is not the stored one is a 409 with the code
`VERSAO_DESATUALIZADA`. Asking for a wording answers 202 at once and the executor calls the AI.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from starlette.concurrency import run_in_threadpool

from app.domain.entities.user import User
from app.presentation.dependencies import Container, current_user, get_container
from app.presentation.schemas.generated import (
    EntryTextIn,
    MoveEntryIn,
    ReportDraftOut,
    ReportDraftViewOut,
    SectionTextIn,
    WordingJobOut,
)

router = APIRouter(prefix="/api/processes", tags=["report-draft"])

ContainerDep = Annotated[Container, Depends(get_container)]
UserDep = Annotated[User, Depends(current_user)]


@router.get("/{process_id}/report-draft", response_model=ReportDraftViewOut)
async def get_report_draft(
    process_id: UUID, actor: UserDep, container: ContainerDep
) -> ReportDraftViewOut:
    view = await run_in_threadpool(container.get_report_draft.execute, actor, process_id)
    return ReportDraftViewOut.of_view(view)


@router.put("/{process_id}/report-draft/entries/{activity_id}", response_model=ReportDraftOut)
async def save_entry(
    process_id: UUID,
    activity_id: UUID,
    body: EntryTextIn,
    actor: UserDep,
    container: ContainerDep,
) -> ReportDraftOut:
    draft = await run_in_threadpool(
        container.save_report_entry.execute,
        actor,
        process_id,
        activity_id,
        body.text,
        body.expected_version,
    )
    return ReportDraftOut.of(draft)


@router.put("/{process_id}/report-draft/sections/{section_key}", response_model=ReportDraftOut)
async def save_section(
    process_id: UUID,
    section_key: str,
    body: SectionTextIn,
    actor: UserDep,
    container: ContainerDep,
) -> ReportDraftOut:
    draft = await run_in_threadpool(
        container.save_report_section.execute,
        actor,
        process_id,
        section_key,
        body.free_text,
        body.expected_version,
    )
    return ReportDraftOut.of(draft)


@router.post("/{process_id}/report-draft/entries/{activity_id}/move", response_model=ReportDraftOut)
async def move_entry(
    process_id: UUID,
    activity_id: UUID,
    body: MoveEntryIn,
    actor: UserDep,
    container: ContainerDep,
) -> ReportDraftOut:
    draft = await run_in_threadpool(
        container.move_report_entry.execute,
        actor,
        process_id,
        activity_id,
        body.section_key,
        body.expected_version,
    )
    return ReportDraftOut.of(draft)


@router.post(
    "/{process_id}/report-draft/sections/{section_key}/wording",
    response_model=WordingJobOut,
    status_code=202,
)
async def request_wording(
    process_id: UUID, section_key: str, actor: UserDep, container: ContainerDep
) -> WordingJobOut:
    job = await run_in_threadpool(container.request_wording.execute, actor, process_id, section_key)
    return WordingJobOut.of(job)


@router.get("/{process_id}/report-draft/wording", response_model=list[WordingJobOut])
async def list_wording_jobs(
    process_id: UUID, actor: UserDep, container: ContainerDep
) -> list[WordingJobOut]:
    jobs = await run_in_threadpool(container.list_wording_jobs.execute, actor, process_id)
    return [WordingJobOut.of(job) for _, job in sorted(jobs.items())]
