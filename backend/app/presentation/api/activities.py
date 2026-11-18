"""Activity routes (ATV-01..ATV-14). Access follows the process: outside it, 404."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from starlette.concurrency import run_in_threadpool

from app.domain.entities.activity import ActivityStatus
from app.domain.entities.user import User
from app.presentation.dependencies import Container, current_user, get_container
from app.presentation.schemas.activities import (
    ActivityCreate,
    ActivityDistinct,
    ActivityOut,
    ActivityStatusChange,
    ActivityUpdate,
)

router = APIRouter(prefix="/api", tags=["activities"])

ContainerDep = Annotated[Container, Depends(get_container)]
UserDep = Annotated[User, Depends(current_user)]


@router.get("/processes/{process_id}/activities", response_model=list[ActivityOut])
async def list_activities(
    process_id: UUID,
    actor: UserDep,
    container: ContainerDep,
    group: int | None = None,
    status: ActivityStatus | None = None,
) -> list[ActivityOut]:
    found = await run_in_threadpool(
        container.list_activities.execute, actor, process_id, group, status
    )
    return [ActivityOut.of(a) for a in found]


@router.post("/processes/{process_id}/activities", response_model=ActivityOut, status_code=201)
async def create_activity(
    process_id: UUID, body: ActivityCreate, actor: UserDep, container: ContainerDep
) -> ActivityOut:
    activity = await run_in_threadpool(
        container.create_activity.execute, actor, process_id, body.to_data(), body.justificativa
    )
    return ActivityOut.of(activity)


@router.get("/activities/{activity_id}", response_model=ActivityOut)
async def get_activity(activity_id: UUID, actor: UserDep, container: ContainerDep) -> ActivityOut:
    activity = await run_in_threadpool(container.get_activity.execute, actor, activity_id)
    return ActivityOut.of(activity)


@router.put("/activities/{activity_id}", response_model=ActivityOut)
async def update_activity(
    activity_id: UUID, body: ActivityUpdate, actor: UserDep, container: ContainerDep
) -> ActivityOut:
    activity = await run_in_threadpool(
        container.update_activity.execute,
        actor,
        activity_id,
        body.to_data(),
        body.expected_version,
        body.justificativa,
    )
    return ActivityOut.of(activity)


@router.post("/activities/{activity_id}/status", response_model=ActivityOut)
async def change_status(
    activity_id: UUID, body: ActivityStatusChange, actor: UserDep, container: ContainerDep
) -> ActivityOut:
    activity = await run_in_threadpool(
        container.change_activity_status.execute,
        actor,
        activity_id,
        body.status,
        body.expected_version,
        body.justificativa,
    )
    return ActivityOut.of(activity)


@router.post("/activities/{activity_id}/distinct", response_model=ActivityOut)
async def mark_distinct(
    activity_id: UUID, body: ActivityDistinct, actor: UserDep, container: ContainerDep
) -> ActivityOut:
    activity = await run_in_threadpool(
        container.mark_activities_distinct.execute,
        actor,
        activity_id,
        body.expected_version,
        body.justificativa,
    )
    return ActivityOut.of(activity)
