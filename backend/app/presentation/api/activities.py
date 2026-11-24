"""Activity routes (ATV-01..ATV-14). Access follows the process: outside it, 404."""

from collections.abc import Sequence
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from starlette.concurrency import run_in_threadpool

from app.application.use_cases.scoring import ActivityListing
from app.domain.entities.activity import Activity, ActivityStatus
from app.domain.entities.user import User
from app.presentation.dependencies import Container, current_user, get_container
from app.presentation.schemas.activities import (
    ActivityBulkValidate,
    ActivityCreate,
    ActivityDistinct,
    ActivityOut,
    ActivitySeparate,
    ActivityStatusChange,
    ActivityUpdate,
    BulkValidateOut,
    MergedOut,
    MergeOut,
    SkippedOut,
)
from app.presentation.schemas.documents import EvidenceOut

router = APIRouter(prefix="/api", tags=["activities"])

ContainerDep = Annotated[Container, Depends(get_container)]
UserDep = Annotated[User, Depends(current_user)]


async def _present(
    container: Container,
    activities: Sequence[Activity],
    described: ActivityListing | None = None,
) -> list[ActivityOut]:
    """The activities with their linked documents (VINC-02), in the order given.

    With `described` (the list and the read of one activity) each also carries its validity, the
    activities merged into it and its predicted points; the answer of a write leaves them empty.
    """
    found = await run_in_threadpool(container.list_evidences.execute, [a.id for a in activities])
    if described is None:
        return [
            ActivityOut.of(a, [EvidenceOut.of(v.evidence, v.document_name) for v in found[a.id]])
            for a in activities
        ]
    return [
        ActivityOut.of(
            a,
            [EvidenceOut.of(v.evidence, v.document_name) for v in found[a.id]],
            validity=described.validity.get(a.id),
            merged=[MergedOut(id=m.id, title=m.title) for m in described.merged.get(a.id, ())],
            predicted_points=described.predicted_points.get(a.id),
        )
        for a in activities
    ]


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
    return await _present(container, found.activities, found)


@router.post("/processes/{process_id}/activities", response_model=ActivityOut, status_code=201)
async def create_activity(
    process_id: UUID, body: ActivityCreate, actor: UserDep, container: ContainerDep
) -> ActivityOut:
    activity = await run_in_threadpool(
        container.create_activity.execute, actor, process_id, body.to_data(), body.justificativa
    )
    return (await _present(container, [activity]))[0]


@router.post("/processes/{process_id}/activities/validate-batch", response_model=BulkValidateOut)
async def validate_batch(
    process_id: UUID, body: ActivityBulkValidate, actor: UserDep, container: ContainerDep
) -> BulkValidateOut:
    """Validates the listed activities that can be validated and lists the skipped ones with the
    reason; one of another process: 404."""
    validated = await run_in_threadpool(
        container.bulk_validate_activities.execute,
        actor,
        process_id,
        body.activity_ids,
        body.justificativa,
    )
    return BulkValidateOut(
        activities=await _present(container, validated.activities),
        skipped=[SkippedOut(id=s.id, reason=s.reason) for s in validated.skipped],
    )


@router.post("/processes/{process_id}/activities/merge-duplicates", response_model=MergeOut)
async def merge_duplicates(
    process_id: UUID, actor: UserDep, container: ContainerDep
) -> MergeOut:
    """Merges the duplicate activities of the process; answers 0 when there is nothing to do."""
    merged = await run_in_threadpool(container.merge_process_duplicates.execute, actor, process_id)
    return MergeOut(merged=merged)


@router.post("/activities/{activity_id}/separate", response_model=ActivityOut)
async def separate_activity(
    activity_id: UUID,
    actor: UserDep,
    container: ContainerDep,
    body: ActivitySeparate | None = None,
) -> ActivityOut:
    """"Não é duplicada": restores a merged activity and marks the two as distinct."""
    activity = await run_in_threadpool(
        container.separate_activity.execute,
        actor,
        activity_id,
        body.expected_version if body else None,
    )
    return (await _present(container, [activity]))[0]


@router.get("/activities/{activity_id}", response_model=ActivityOut)
async def get_activity(activity_id: UUID, actor: UserDep, container: ContainerDep) -> ActivityOut:
    found = await run_in_threadpool(container.get_activity.execute, actor, activity_id)
    return (await _present(container, found.activities, found))[0]


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
    return (await _present(container, [activity]))[0]


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
    return (await _present(container, [activity]))[0]


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
    return (await _present(container, [activity]))[0]
