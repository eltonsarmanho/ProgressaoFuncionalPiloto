"""Generated document routes (TAB-01, TAB-07, TAB-08, VER-03, VER-04, VER-06, DEL-13): ask for a
generation, list the versions, read one and download its file.

Access follows the process: outside it, 404. Asking answers at once with the row in GERANDO and
the executor does the work; a file is served exactly as stored, as an attachment, with the SHA-256
of its content as `ETag`. The name of the download is made on the server and carries no data of
the professor.
"""

from typing import Annotated
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool

from app.domain.entities.generated import DocumentFormat, DocumentKind
from app.domain.entities.user import User
from app.domain.errors import NotFound
from app.presentation.dependencies import Container, current_user, get_container
from app.presentation.schemas.generated import (
    GeneratedDocumentDetailOut,
    GeneratedDocumentOut,
    GenerationRequest,
)

router = APIRouter(prefix="/api", tags=["generated-documents"])

ContainerDep = Annotated[Container, Depends(get_container)]
UserDep = Annotated[User, Depends(current_user)]


@router.post(
    "/processes/{process_id}/generated-documents",
    response_model=GeneratedDocumentOut,
    status_code=202,
)
async def request_generation(
    process_id: UUID, body: GenerationRequest, actor: UserDep, container: ContainerDep
) -> GeneratedDocumentOut:
    row = await run_in_threadpool(
        container.request_generation.execute, actor, process_id, body.kind
    )
    return GeneratedDocumentOut.of(row)


@router.get(
    "/processes/{process_id}/generated-documents", response_model=list[GeneratedDocumentOut]
)
async def list_generated_documents(
    process_id: UUID, actor: UserDep, container: ContainerDep, kind: DocumentKind | None = None
) -> list[GeneratedDocumentOut]:
    rows = await run_in_threadpool(
        container.list_generated_documents.execute, actor, process_id, kind
    )
    return [GeneratedDocumentOut.of(r) for r in rows]


@router.get("/generated-documents/{generation_id}", response_model=GeneratedDocumentDetailOut)
async def get_generated_document(
    generation_id: UUID, actor: UserDep, container: ContainerDep
) -> GeneratedDocumentDetailOut:
    row = await run_in_threadpool(container.get_generated_document.execute, actor, generation_id)
    return GeneratedDocumentDetailOut.of(row)


@router.get("/generated-documents/{generation_id}/files/{extension}")
async def download_generated_file(
    generation_id: UUID, extension: str, actor: UserDep, container: ContainerDep
) -> FileResponse:
    """`extension` is `docx` or `pdf`; any other is a file that does not exist."""
    try:
        fmt = DocumentFormat(extension.upper())
    except ValueError:
        raise NotFound("Arquivo não encontrado") from None
    found = await run_in_threadpool(
        container.download_generated_file.execute, actor, generation_id, fmt
    )
    headers = {
        "Content-Disposition": f"attachment; filename*=UTF-8''{quote(found.filename, safe='')}",
        "X-Content-Type-Options": "nosniff",
        "ETag": f'"{found.sha256}"',
        "Cache-Control": "private, no-cache",
    }
    return FileResponse(found.path, media_type=found.content_type, headers=headers)
