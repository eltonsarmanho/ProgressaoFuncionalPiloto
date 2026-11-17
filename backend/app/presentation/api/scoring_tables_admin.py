"""Scoring table administration routes (ADM-01..11): only ADMIN writes; reads are open."""

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from app.application.use_cases.scoring_admin import InvalidCsv
from app.domain.entities.scoring import TableStatus
from app.domain.entities.user import User
from app.domain.errors import ValidationFailed
from app.presentation.dependencies import Container, current_user, get_container
from app.presentation.schemas.scoring import CriterionOut, TableOut, VersionOut
from app.presentation.schemas.scoring_admin import (
    CriterionChangeIn,
    TableCreateIn,
    TableDuplicateIn,
    TableHistoryOut,
    UnitsIn,
    VersionCreateIn,
)

router = APIRouter(prefix="/api", tags=["scoring-tables-admin"])

ContainerDep = Annotated[Container, Depends(get_container)]
UserDep = Annotated[User, Depends(current_user)]


@router.post("/scoring-tables", response_model=TableOut, status_code=201)
async def create_table(body: TableCreateIn, actor: UserDep, container: ContainerDep) -> TableOut:
    view = await run_in_threadpool(
        container.create_scoring_table.execute, actor, **body.model_dump()
    )
    return TableOut.of(view)


@router.post("/scoring-tables/{table_id}/duplicate", response_model=TableOut, status_code=201)
async def duplicate_table(
    table_id: UUID, body: TableDuplicateIn, actor: UserDep, container: ContainerDep
) -> TableOut:
    view = await run_in_threadpool(
        container.duplicate_scoring_table.execute, actor, table_id, body.new_name, body.unit_ids
    )
    return TableOut.of(view)


@router.post("/scoring-tables/{table_id}/versions", response_model=VersionOut, status_code=201)
async def create_version(
    table_id: UUID, body: VersionCreateIn, actor: UserDep, container: ContainerDep
) -> VersionOut:
    view = await run_in_threadpool(
        container.create_scoring_version.execute, actor, table_id, **body.model_dump()
    )
    return VersionOut.of(view)


@router.put("/scoring-versions/{version_id}/criteria/{group}/{item}", response_model=CriterionOut)
async def update_criterion(
    version_id: UUID,
    group: int,
    item: int,
    body: CriterionChangeIn,
    actor: UserDep,
    container: ContainerDep,
) -> CriterionOut:
    view = await run_in_threadpool(
        container.update_version_criteria.execute,
        actor,
        version_id,
        group,
        item,
        body.changes,
        body.change_reference,
    )
    return CriterionOut.of(view.version.get_criterion(group, item))


def _optional_date(value: str | None) -> date | None:
    if value is None or not value.strip():
        return None
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        raise ValidationFailed("valid_to", "Data inválida; use AAAA-MM-DD") from None


@router.post(
    "/scoring-tables/{table_id}/versions/import", response_model=VersionOut, status_code=201
)
async def import_criteria(
    table_id: UUID,
    actor: UserDep,
    container: ContainerDep,
    file: Annotated[UploadFile, File()],
    valid_from: Annotated[date, Form()],
    norm_reference: Annotated[str, Form()],
    valid_to: Annotated[str | None, Form()] = None,
    status: Annotated[TableStatus, Form()] = TableStatus.PENDENTE_VALIDACAO,
):
    try:
        text = (await file.read()).decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ValidationFailed("file", "O arquivo deve estar em UTF-8") from None
    try:
        view = await run_in_threadpool(
            container.import_criteria_csv.execute,
            actor,
            table_id,
            valid_from,
            _optional_date(valid_to),
            norm_reference,
            text,
            status,
        )
    except InvalidCsv as exc:
        return JSONResponse(
            {
                "detail": [
                    {"field": "file", "message": f"linha {e.line}, campo {e.field}: {e.message}"}
                    for e in exc.errors
                ]
            },
            status_code=422,
        )
    return VersionOut.of(view)


@router.put("/scoring-tables/{table_id}/units", response_model=TableOut)
async def set_units(
    table_id: UUID, body: UnitsIn, actor: UserDep, container: ContainerDep
) -> TableOut:
    view = await run_in_threadpool(
        container.set_table_units.execute, actor, table_id, body.unit_ids
    )
    return TableOut.of(view)


@router.get("/scoring-tables/{table_id}/history", response_model=TableHistoryOut)
async def table_history(table_id: UUID, _: UserDep, container: ContainerDep) -> TableHistoryOut:
    history = await run_in_threadpool(container.table_history.execute, table_id)
    return TableHistoryOut.of(history)
