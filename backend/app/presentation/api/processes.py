"""Process routes (PROC-01..PROC-04, PROC-12..PROC-14; AUTH-08/09; AUD-03)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from starlette.concurrency import run_in_threadpool

from app.application.use_cases.processes import ProcessData
from app.domain.entities.user import User
from app.presentation.dependencies import Container, current_user, get_container
from app.presentation.schemas.processes import (
    HistoryEventOut,
    ProcessCreate,
    ProcessOut,
    ProcessSummary,
    ProcessUpdate,
    StatusChange,
)

router = APIRouter(prefix="/api/processes", tags=["processes"])

ContainerDep = Annotated[Container, Depends(get_container)]
UserDep = Annotated[User, Depends(current_user)]


@router.post("", response_model=ProcessOut, status_code=201)
async def create_process(
    body: ProcessCreate, actor: UserDep, container: ContainerDep
) -> ProcessOut:
    data = ProcessData(**body.model_dump(exclude={"professor_id", "unit_id"}))
    result = await run_in_threadpool(
        container.create_process.execute, actor, body.professor_id, body.unit_id, data
    )
    return ProcessOut.of(result)


@router.get("", response_model=list[ProcessSummary])
async def list_processes(actor: UserDep, container: ContainerDep) -> list[ProcessSummary]:
    results = await run_in_threadpool(container.list_processes.execute, actor)
    return [ProcessSummary.of(r) for r in results]


@router.get("/{process_id}", response_model=ProcessOut)
async def get_process(process_id: UUID, actor: UserDep, container: ContainerDep) -> ProcessOut:
    return ProcessOut.of(await run_in_threadpool(container.get_process.execute, actor, process_id))


@router.put("/{process_id}", response_model=ProcessOut)
async def update_process(
    process_id: UUID, body: ProcessUpdate, actor: UserDep, container: ContainerDep
) -> ProcessOut:
    data = ProcessData(**body.model_dump(exclude={"expected_version", "justificativa"}))
    result = await run_in_threadpool(
        container.update_process.execute,
        actor,
        process_id,
        data,
        body.justificativa,
        body.expected_version,
    )
    return ProcessOut.of(result)


@router.post("/{process_id}/status", response_model=ProcessOut)
async def change_status(
    process_id: UUID, body: StatusChange, actor: UserDep, container: ContainerDep
) -> ProcessOut:
    result = await run_in_threadpool(
        container.change_process_status.execute,
        actor,
        process_id,
        body.status,
        body.expected_version,
        body.justificativa,
    )
    return ProcessOut.of(result)


@router.get("/{process_id}/history", response_model=list[HistoryEventOut])
async def process_history(
    process_id: UUID, actor: UserDep, container: ContainerDep
) -> list[HistoryEventOut]:
    events = await run_in_threadpool(container.process_history.execute, actor, process_id)
    return [HistoryEventOut.of(e) for e in events]
