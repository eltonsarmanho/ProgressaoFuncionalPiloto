"""Scoring of a process: table choice and calculated result (SEL-02..SEL-08, CALC-12)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from starlette.concurrency import run_in_threadpool

from app.domain.entities.user import User
from app.presentation.dependencies import Container, current_user, get_container
from app.presentation.schemas.scoring import ProcessScoreOut, TableChoiceIn, TableStateOut

router = APIRouter(prefix="/api/processes", tags=["scoring"])

ContainerDep = Annotated[Container, Depends(get_container)]
UserDep = Annotated[User, Depends(current_user)]


@router.get("/{process_id}/scoring/table", response_model=TableStateOut)
async def get_table(process_id: UUID, actor: UserDep, container: ContainerDep) -> TableStateOut:
    state = await run_in_threadpool(container.suggest_scoring_table.execute, actor, process_id)
    return TableStateOut.of(state)


@router.put("/{process_id}/scoring/table", response_model=TableStateOut)
async def choose_table(
    process_id: UUID, body: TableChoiceIn, actor: UserDep, container: ContainerDep
) -> TableStateOut:
    state = await run_in_threadpool(
        container.choose_process_table.execute,
        actor,
        process_id,
        body.version_id,
        body.expected_version,
        body.justificativa,
    )
    return TableStateOut.of(state)


@router.get("/{process_id}/scoring", response_model=ProcessScoreOut)
async def get_scoring(process_id: UUID, actor: UserDep, container: ContainerDep) -> ProcessScoreOut:
    score = await run_in_threadpool(container.calculate_process_score.execute, actor, process_id)
    return ProcessScoreOut.of(score)
