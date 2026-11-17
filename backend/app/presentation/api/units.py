"""Academic unit routes (UNIT-01): everyone lists, only ADMIN changes."""

from dataclasses import asdict
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from starlette.concurrency import run_in_threadpool

from app.application.use_cases.units import UnitData
from app.domain.entities.user import User
from app.presentation.dependencies import Container, current_user, get_container
from app.presentation.schemas.units import UnitIn, UnitOut

router = APIRouter(prefix="/api/units", tags=["units"])

ContainerDep = Annotated[Container, Depends(get_container)]
UserDep = Annotated[User, Depends(current_user)]


def _out(unit) -> UnitOut:
    return UnitOut(**asdict(unit))


@router.get("", response_model=list[UnitOut])
async def list_units(_: UserDep, container: ContainerDep) -> list[UnitOut]:
    return [_out(u) for u in await run_in_threadpool(container.list_units.execute)]


@router.post("", response_model=UnitOut, status_code=201)
async def create_unit(body: UnitIn, actor: UserDep, container: ContainerDep) -> UnitOut:
    unit = await run_in_threadpool(
        container.create_unit.execute, actor, UnitData(**body.model_dump())
    )
    return _out(unit)


@router.put("/{unit_id}", response_model=UnitOut)
async def update_unit(
    unit_id: UUID, body: UnitIn, actor: UserDep, container: ContainerDep
) -> UnitOut:
    unit = await run_in_threadpool(
        container.update_unit.execute, actor, unit_id, UnitData(**body.model_dump())
    )
    return _out(unit)


@router.post("/{unit_id}/archive", response_model=UnitOut)
async def archive_unit(unit_id: UUID, actor: UserDep, container: ContainerDep) -> UnitOut:
    return _out(await run_in_threadpool(container.archive_unit.execute, actor, unit_id))
