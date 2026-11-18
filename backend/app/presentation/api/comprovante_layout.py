"""Comprovante arrangement routes (ARR-01, ARR-02, ARR-06, ARR-07, UIG-03): read the arrangement
in force with the numbering it will have, and save the one the user arranged.

Access follows the process: outside it, 404. A read never writes: without a saved arrangement the
one derived from the links comes back with `version` 0, and the first save uses `expected_version`
0. A version that is not the stored one is a 409 with the code `VERSAO_DESATUALIZADA`. Saving
answers with the view as it is after the save, so the numbering shown is the new one.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from starlette.concurrency import run_in_threadpool

from app.domain.entities.user import User
from app.presentation.dependencies import Container, current_user, get_container
from app.presentation.schemas.generated import LayoutSaveIn, LayoutViewOut

router = APIRouter(prefix="/api/processes", tags=["comprovante-layout"])

ContainerDep = Annotated[Container, Depends(get_container)]
UserDep = Annotated[User, Depends(current_user)]


@router.get("/{process_id}/comprovante-layout", response_model=LayoutViewOut)
async def get_layout(process_id: UUID, actor: UserDep, container: ContainerDep) -> LayoutViewOut:
    view = await run_in_threadpool(container.get_comprovante_layout.execute, actor, process_id)
    return LayoutViewOut.of(view)


@router.put("/{process_id}/comprovante-layout", response_model=LayoutViewOut)
async def save_layout(
    process_id: UUID, body: LayoutSaveIn, actor: UserDep, container: ContainerDep
) -> LayoutViewOut:
    await run_in_threadpool(
        container.save_comprovante_layout.execute,
        actor,
        process_id,
        body.expected_version,
        [entry.to_domain() for entry in body.activities],
    )
    view = await run_in_threadpool(container.get_comprovante_layout.execute, actor, process_id)
    return LayoutViewOut.of(view)
