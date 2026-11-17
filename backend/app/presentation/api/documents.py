"""Document routes: upload, list and detail (DOC-01..04, 07, 12, 14, 15, REV-01).

Access follows the process: outside it, 404. Each uploaded part is copied in chunks to a
temporary file while its SHA-256 and size are computed; a part above the size limit stops being
read. The temporary files are removed whatever happens.
"""

import hashlib
import tempfile
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, UploadFile
from starlette.concurrency import run_in_threadpool

from app.application.use_cases.documents import IncomingFile
from app.domain.entities.document import DocumentStatus
from app.domain.entities.extraction import DocumentType
from app.domain.entities.user import User
from app.presentation.dependencies import Container, current_user, get_container
from app.presentation.schemas.documents import (
    DocumentDetailOut,
    DocumentOut,
    UploadResultOut,
)

router = APIRouter(prefix="/api", tags=["documents"])

ContainerDep = Annotated[Container, Depends(get_container)]
UserDep = Annotated[User, Depends(current_user)]

CHUNK_BYTES = 1024 * 1024
CREATED = 201
MULTI_STATUS = 207


async def _stage(part: UploadFile, target: Path, max_bytes: int) -> IncomingFile:
    """Copies the part to `target`, hashing as it goes; stops one byte past the limit.

    A part that went past the limit is kept truncated: the use case refuses it by size.
    """
    digest = hashlib.sha256()
    size = 0
    with target.open("wb") as out:
        while chunk := await part.read(CHUNK_BYTES):
            chunk = chunk[: max_bytes + 1 - size]
            digest.update(chunk)
            out.write(chunk)
            size += len(chunk)
            if size > max_bytes:
                break
    await part.close()
    return IncomingFile(target, part.filename or "", part.content_type, size, digest.hexdigest())


@router.post("/processes/{process_id}/documents", response_model=list[UploadResultOut])
async def upload_documents(
    process_id: UUID,
    file: list[UploadFile],
    response: Response,
    actor: UserDep,
    container: ContainerDep,
) -> list[UploadResultOut]:
    max_bytes = container.settings.max_upload_mb * 1024 * 1024
    with tempfile.TemporaryDirectory() as scratch:
        staged = [
            await _stage(part, Path(scratch) / str(index), max_bytes)
            for index, part in enumerate(file)
        ]
        results = await run_in_threadpool(
            container.upload_documents.execute, actor, process_id, staged
        )
    response.status_code = (
        CREATED if all(r.status_code == CREATED for r in results) else MULTI_STATUS
    )
    return [UploadResultOut.of(r) for r in results]


@router.get("/processes/{process_id}/documents", response_model=list[DocumentOut])
async def list_documents(
    process_id: UUID,
    actor: UserDep,
    container: ContainerDep,
    status: DocumentStatus | None = None,
    document_type: Annotated[DocumentType | None, Query(alias="type")] = None,
) -> list[DocumentOut]:
    found = await run_in_threadpool(
        container.list_documents.execute,
        actor,
        process_id,
        status,
        document_type.value if document_type else None,
    )
    return [DocumentOut.of(d) for d in found]


@router.get("/documents/{document_id}", response_model=DocumentDetailOut)
async def get_document(
    document_id: UUID, actor: UserDep, container: ContainerDep
) -> DocumentDetailOut:
    detail = await run_in_threadpool(container.get_document.execute, actor, document_id)
    return DocumentDetailOut.of(detail)
