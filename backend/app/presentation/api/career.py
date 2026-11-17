"""Career version routes (CARR-08): everyone lists, only ADMIN creates or edits."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from starlette.concurrency import run_in_threadpool

from app.domain.entities.user import User
from app.presentation.dependencies import Container, current_user, get_container
from app.presentation.schemas.career import CareerVersionIn, CareerVersionOut

router = APIRouter(prefix="/api/career-structures", tags=["career"])

ContainerDep = Annotated[Container, Depends(get_container)]
UserDep = Annotated[User, Depends(current_user)]


@router.get("/{code}/versions", response_model=list[CareerVersionOut])
async def list_versions(code: str, _: UserDep, container: ContainerDep) -> list[CareerVersionOut]:
    views = await run_in_threadpool(container.list_career_versions.execute, code)
    return [CareerVersionOut.of(v) for v in views]


@router.post("/{code}/versions", response_model=CareerVersionOut, status_code=201)
async def create_version(
    code: str, body: CareerVersionIn, actor: UserDep, container: ContainerDep
) -> CareerVersionOut:
    view = await run_in_threadpool(
        container.create_career_version.execute, actor, code, body.to_entity()
    )
    return CareerVersionOut.of(view)


@router.put("/{code}/versions/{version_id}", response_model=CareerVersionOut)
async def update_version(
    code: str, version_id: UUID, body: CareerVersionIn, actor: UserDep, container: ContainerDep
) -> CareerVersionOut:
    view = await run_in_threadpool(
        container.update_career_version.execute, actor, code, version_id, body.to_entity()
    )
    return CareerVersionOut.of(view)
