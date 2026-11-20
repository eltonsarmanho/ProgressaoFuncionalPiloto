"""Evidence routes: link an activity to a document page and remove the link (VINC-02, 03, 05).

Access follows the process: outside it, 404.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from starlette.concurrency import run_in_threadpool

from app.domain.entities.user import User
from app.presentation.dependencies import Container, current_user, get_container
from app.presentation.schemas.documents import EvidenceCreate, EvidenceOut

router = APIRouter(prefix="/api/activities", tags=["evidences"])

ContainerDep = Annotated[Container, Depends(get_container)]
UserDep = Annotated[User, Depends(current_user)]


@router.post("/{activity_id}/evidences", response_model=EvidenceOut, status_code=201)
async def link_evidence(
    activity_id: UUID, body: EvidenceCreate, actor: UserDep, container: ContainerDep
) -> EvidenceOut:
    evidence = await run_in_threadpool(
        container.link_evidence.execute,
        actor,
        activity_id,
        body.document_id,
        body.page,
        body.justificativa,
    )
    views = await run_in_threadpool(container.list_evidences.execute, [activity_id])
    view = next(v for v in views[activity_id] if v.evidence.id == evidence.id)
    return EvidenceOut.of(view.evidence, view.document_name)


@router.delete("/{activity_id}/evidences/{evidence_id}", status_code=204)
async def unlink_evidence(
    activity_id: UUID, evidence_id: UUID, actor: UserDep, container: ContainerDep
) -> Response:
    await run_in_threadpool(container.unlink_evidence.execute, actor, activity_id, evidence_id)
    return Response(status_code=204)
