"""Dossier order route (ORD-01, ORD-02): the documents of the dossier in delivery order, with the
ones the system generates marked. The list comes from the versioned configuration file, read at
every call, and needs a session like every other route."""

from typing import Annotated

from fastapi import APIRouter, Depends
from starlette.concurrency import run_in_threadpool

from app.presentation.dependencies import Container, get_container
from app.presentation.schemas.generated import DossierItemOut

router = APIRouter(prefix="/api", tags=["dossier"])

ContainerDep = Annotated[Container, Depends(get_container)]


@router.get("/dossier-order", response_model=list[DossierItemOut])
async def dossier_order(container: ContainerDep) -> list[DossierItemOut]:
    items = await run_in_threadpool(container.dossier_order)
    return [DossierItemOut.of(item) for item in items]
