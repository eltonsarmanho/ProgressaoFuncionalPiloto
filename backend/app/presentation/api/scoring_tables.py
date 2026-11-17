"""Scoring table read routes (TAB-08): every authenticated user may read."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from starlette.concurrency import run_in_threadpool

from app.domain.entities.user import User
from app.presentation.dependencies import Container, current_user, get_container
from app.presentation.schemas.scoring import TableOut, VersionOut, VersionSummaryOut

router = APIRouter(prefix="/api", tags=["scoring-tables"])

ContainerDep = Annotated[Container, Depends(get_container)]
UserDep = Annotated[User, Depends(current_user)]


@router.get("/scoring-tables", response_model=list[TableOut])
async def list_tables(_: UserDep, container: ContainerDep) -> list[TableOut]:
    views = await run_in_threadpool(container.list_scoring_tables.execute)
    return [TableOut.of(v) for v in views]


@router.get("/scoring-tables/{table_id}/versions", response_model=list[VersionSummaryOut])
async def list_versions(
    table_id: UUID, _: UserDep, container: ContainerDep
) -> list[VersionSummaryOut]:
    views = await run_in_threadpool(container.list_table_versions.execute, table_id)
    return [VersionSummaryOut.of(v) for v in views]


@router.get("/scoring-versions/{version_id}", response_model=VersionOut)
async def get_version(version_id: UUID, _: UserDep, container: ContainerDep) -> VersionOut:
    view = await run_in_threadpool(container.get_scoring_version.execute, version_id)
    return VersionOut.of(view)
