"""Board routes (PORT-01, PORT-02, PORT-05..08, PORT-10..12, PAR-01, PAR-12, PAR-13, BNAV-02,
BNAV-03): read the board, save the data of the ordinance, send, replace, re-read and view its
file, save the fields of the Parecer and the city of the Requerimento.

Access follows the process: outside it, 404. A concluded or archived process is read but refuses
every write with 409 `PROCESSO_SOMENTE_LEITURA`. The first save of each part sends
`expected_version` 0; a version that is not the stored one is a 409 `VERSAO_DESATUALIZADA`.
Nothing here asks for a justification (regra 5).
"""

import tempfile
from pathlib import Path
from typing import Annotated
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, Form, UploadFile
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool

from app.domain.entities.user import User
from app.presentation.api.documents import _stage
from app.presentation.dependencies import Container, current_user, get_container
from app.presentation.schemas.board import (
    BoardOut,
    OpinionIn,
    OpinionOut,
    OrdinanceDataIn,
    OrdinanceOut,
    RequestSettingsIn,
    RequestSettingsOut,
    RereadIn,
)

router = APIRouter(prefix="/api/processes", tags=["board"])

ContainerDep = Annotated[Container, Depends(get_container)]
UserDep = Annotated[User, Depends(current_user)]


@router.get("/{process_id}/board", response_model=BoardOut)
async def get_board(process_id: UUID, actor: UserDep, container: ContainerDep) -> BoardOut:
    view = await run_in_threadpool(container.get_board.execute, actor, process_id)
    return BoardOut.of(view)


@router.put("/{process_id}/board/ordinance", response_model=OrdinanceOut)
async def save_ordinance(
    process_id: UUID, body: OrdinanceDataIn, actor: UserDep, container: ContainerDep
) -> OrdinanceOut:
    ordinance = await run_in_threadpool(
        container.save_ordinance_data.execute,
        actor,
        process_id,
        body.number,
        body.ordinance_date,
        body.member_inputs(),
        body.expected_version,
    )
    return OrdinanceOut.of(ordinance)


@router.put("/{process_id}/board/ordinance/file", response_model=OrdinanceOut)
async def upload_ordinance_file(
    process_id: UUID,
    file: UploadFile,
    expected_version: Annotated[int, Form()],
    actor: UserDep,
    container: ContainerDep,
    replace: Annotated[bool, Form()] = False,
) -> OrdinanceOut:
    """Stores the file and queues its reading; a second file asks for `replace` (409)."""
    max_bytes = container.settings.max_upload_mb * 1024 * 1024
    with tempfile.TemporaryDirectory() as scratch:
        staged = await _stage(file, Path(scratch) / "0", max_bytes)
        ordinance = await run_in_threadpool(
            container.upload_ordinance.execute,
            actor,
            process_id,
            staged,
            expected_version,
            replace,
        )
    return OrdinanceOut.of(ordinance)


@router.post("/{process_id}/board/ordinance/reread", response_model=OrdinanceOut)
async def reread_ordinance(
    process_id: UUID, body: RereadIn, actor: UserDep, container: ContainerDep
) -> OrdinanceOut:
    ordinance = await run_in_threadpool(
        container.reread_ordinance.execute, actor, process_id, body.expected_version
    )
    return OrdinanceOut.of(ordinance)


@router.get("/{process_id}/board/ordinance/file")
async def get_ordinance_file(
    process_id: UUID, actor: UserDep, container: ContainerDep
) -> FileResponse:
    """The stored file, shown inline in a sandbox and never sniffed."""
    found = await run_in_threadpool(container.download_ordinance_file.execute, actor, process_id)
    headers = {
        "Content-Disposition": f"inline; filename*=UTF-8''{quote(found.name, safe='')}",
        "X-Content-Type-Options": "nosniff",
        "Content-Security-Policy": "sandbox",
    }
    return FileResponse(found.path, media_type=found.mime, headers=headers)


@router.put("/{process_id}/board/opinion", response_model=OpinionOut)
async def save_opinion(
    process_id: UUID, body: OpinionIn, actor: UserDep, container: ContainerDep
) -> OpinionOut:
    opinion = await run_in_threadpool(
        container.save_opinion.execute,
        actor,
        process_id,
        body.conclusion,
        body.opinion_date,
        body.place,
        body.notes,
        body.expected_version,
    )
    return OpinionOut.of(opinion)


@router.put("/{process_id}/request-settings", response_model=RequestSettingsOut)
async def save_request_settings(
    process_id: UUID, body: RequestSettingsIn, actor: UserDep, container: ContainerDep
) -> RequestSettingsOut:
    settings = await run_in_threadpool(
        container.save_request_settings.execute,
        actor,
        process_id,
        body.city,
        body.expected_version,
    )
    return RequestSettingsOut.of(settings)
