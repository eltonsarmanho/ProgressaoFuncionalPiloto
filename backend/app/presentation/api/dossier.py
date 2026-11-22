"""Dossier routes. `/dossier-order` (ORD-01, ORD-02) lists the documents of the dossier in delivery
order, with the ones the system generates marked, and keeps its format. `/processes/{id}/dossier`
(DOS-01 to DOS-06) is the checklist of one process and `PUT .../dossier/items/{key}` marks or
unmarks "Entregue" on an item the system does not produce (DOS-04).

The list comes from the versioned configuration file, read at every call, and every route needs a
session. Access follows the process: outside it, 404; a concluded or archived process is read but
refuses the mark with 409 `PROCESSO_SOMENTE_LEITURA`. No justification is asked (regra 5).
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from starlette.concurrency import run_in_threadpool

from app.domain.entities.user import User
from app.presentation.dependencies import Container, current_user, get_container
from app.presentation.schemas.generated import ChecklistItemOut, DeliveryIn, DossierItemOut

router = APIRouter(prefix="/api", tags=["dossier"])

ContainerDep = Annotated[Container, Depends(get_container)]
UserDep = Annotated[User, Depends(current_user)]


@router.get("/dossier-order", response_model=list[DossierItemOut])
async def dossier_order(container: ContainerDep) -> list[DossierItemOut]:
    items = await run_in_threadpool(container.dossier_order)
    return [DossierItemOut.of(item) for item in items]


@router.get("/processes/{process_id}/dossier", response_model=list[ChecklistItemOut])
async def get_dossier(
    process_id: UUID, actor: UserDep, container: ContainerDep
) -> list[ChecklistItemOut]:
    items = await run_in_threadpool(container.get_dossier.execute, actor, process_id)
    return [ChecklistItemOut.of(item) for item in items]


@router.put("/processes/{process_id}/dossier/items/{key}", response_model=list[ChecklistItemOut])
async def set_delivery(
    process_id: UUID, key: str, body: DeliveryIn, actor: UserDep, container: ContainerDep
) -> list[ChecklistItemOut]:
    items = await run_in_threadpool(
        container.set_dossier_delivery.execute, actor, process_id, key, body.entregue
    )
    return [ChecklistItemOut.of(item) for item in items]
