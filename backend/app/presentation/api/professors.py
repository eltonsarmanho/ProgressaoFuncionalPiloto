"""Professor routes (DOC-01..DOC-05)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from starlette.concurrency import run_in_threadpool

from app.application.use_cases.professors import ProfessorData
from app.domain.entities.user import User
from app.presentation.dependencies import Container, current_user, get_container
from app.presentation.schemas.professors import (
    ProfessorIn,
    ProfessorOut,
    ProfessorUpdate,
    VersionIn,
)

router = APIRouter(prefix="/api/professors", tags=["professors"])

ContainerDep = Annotated[Container, Depends(get_container)]
UserDep = Annotated[User, Depends(current_user)]


def _data(body: ProfessorIn) -> ProfessorData:
    return ProfessorData(**body.model_dump(exclude={"expected_version"}))


@router.post("", response_model=ProfessorOut, status_code=201)
async def create_professor(
    body: ProfessorIn, actor: UserDep, container: ContainerDep
) -> ProfessorOut:
    view = await run_in_threadpool(container.create_professor.execute, actor, _data(body))
    return ProfessorOut.of(view)


@router.get("", response_model=list[ProfessorOut])
async def list_professors(actor: UserDep, container: ContainerDep) -> list[ProfessorOut]:
    views = await run_in_threadpool(container.list_professors.execute, actor)
    return [ProfessorOut.of(v) for v in views]


@router.get("/{professor_id}", response_model=ProfessorOut)
async def get_professor(
    professor_id: UUID, actor: UserDep, container: ContainerDep
) -> ProfessorOut:
    view = await run_in_threadpool(container.get_professor.execute, actor, professor_id)
    return ProfessorOut.of(view)


@router.put("/{professor_id}", response_model=ProfessorOut)
async def update_professor(
    professor_id: UUID, body: ProfessorUpdate, actor: UserDep, container: ContainerDep
) -> ProfessorOut:
    view = await run_in_threadpool(
        container.update_professor.execute,
        actor,
        professor_id,
        _data(body),
        body.expected_version,
    )
    return ProfessorOut.of(view)


@router.post("/{professor_id}/archive", response_model=ProfessorOut)
async def archive_professor(
    professor_id: UUID, body: VersionIn, actor: UserDep, container: ContainerDep
) -> ProfessorOut:
    view = await run_in_threadpool(
        container.archive_professor.execute, actor, professor_id, body.expected_version
    )
    return ProfessorOut.of(view)
