"""Norm routes (NBASE-01..10, NLIST-01, NLIST-02): everyone reads, only ADMIN writes."""

import tempfile
from pathlib import Path
from typing import Annotated
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, Form, UploadFile
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool

from app.application.use_cases.norms import MAX_FILE_BYTES
from app.domain.entities.user import User
from app.domain.repositories.ports import StagedNormFile
from app.presentation.api.documents import _stage
from app.presentation.dependencies import Container, current_user, get_container
from app.presentation.schemas.norms import NormIn, NormOut, NormUpdate, VersionIn

router = APIRouter(prefix="/api/norms", tags=["norms"])

ContainerDep = Annotated[Container, Depends(get_container)]
UserDep = Annotated[User, Depends(current_user)]


async def _fresh(container: Container, actor: User, norm_id: UUID) -> NormOut:
    """The norm as read after a write, with the rules linked to it."""
    return NormOut.of(await run_in_threadpool(container.get_norm.execute, actor, norm_id))


@router.get("", response_model=list[NormOut])
async def list_norms(
    actor: UserDep, container: ContainerDep, include_archived: bool = False
) -> list[NormOut]:
    found = await run_in_threadpool(container.list_norms.execute, actor, include_archived)
    return [NormOut.of(n) for n in found]


@router.post("", response_model=NormOut, status_code=201)
async def create_norm(body: NormIn, actor: UserDep, container: ContainerDep) -> NormOut:
    norm = await run_in_threadpool(
        container.create_norm.execute, actor, body.code, body.fields()
    )
    return await _fresh(container, actor, norm.id)


@router.get("/{norm_id}", response_model=NormOut)
async def get_norm(norm_id: UUID, actor: UserDep, container: ContainerDep) -> NormOut:
    return await _fresh(container, actor, norm_id)


@router.put("/{norm_id}", response_model=NormOut)
async def update_norm(
    norm_id: UUID, body: NormUpdate, actor: UserDep, container: ContainerDep
) -> NormOut:
    await run_in_threadpool(
        container.update_norm.execute, actor, norm_id, body.fields(), body.expected_version
    )
    return await _fresh(container, actor, norm_id)


@router.post("/{norm_id}/archive", response_model=NormOut)
async def archive_norm(
    norm_id: UUID, body: VersionIn, actor: UserDep, container: ContainerDep
) -> NormOut:
    await run_in_threadpool(
        container.archive_norm.execute, actor, norm_id, body.expected_version
    )
    return await _fresh(container, actor, norm_id)


@router.put("/{norm_id}/file", response_model=NormOut)
async def attach_norm_file(
    norm_id: UUID,
    file: UploadFile,
    expected_version: Annotated[int, Form()],
    actor: UserDep,
    container: ContainerDep,
) -> NormOut:
    with tempfile.TemporaryDirectory() as scratch:
        incoming = await _stage(file, Path(scratch) / "0", MAX_FILE_BYTES)
        staged = StagedNormFile(incoming.path, incoming.original_name)
        await run_in_threadpool(
            container.attach_norm_file.execute, actor, norm_id, staged, expected_version
        )
    return await _fresh(container, actor, norm_id)


@router.get("/{norm_id}/file")
async def get_norm_file(norm_id: UUID, actor: UserDep, container: ContainerDep) -> FileResponse:
    """The stored PDF, shown inline in a sandbox and never sniffed."""
    path, name = await run_in_threadpool(container.download_norm_file.execute, actor, norm_id)
    headers = {
        "Content-Disposition": f"inline; filename*=UTF-8''{quote(name, safe='')}",
        "X-Content-Type-Options": "nosniff",
        "Content-Security-Policy": "sandbox",
    }
    return FileResponse(path, media_type="application/pdf", headers=headers)
