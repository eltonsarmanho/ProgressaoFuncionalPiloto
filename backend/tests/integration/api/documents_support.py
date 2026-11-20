"""Fixtures and helpers shared by the document API tests (T36..T41)."""

import hashlib
import uuid
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from functools import lru_cache
from types import SimpleNamespace

from app.domain.entities.document import DocumentStatus, PageText, TextMethod
from app.domain.repositories.ports import JobStatus
from tests.integration.documents.factories import make_document, make_run
from tests.support import synthetic_docs as synth


@lru_cache
def pdf(label: str) -> bytes:
    """A valid one-page PDF that differs from every other label; the same label, the same bytes."""
    return synth.pdf_with_text([f"Documento ficticio numero {label}"])


def files_of(*files):
    """Multipart `file` parts from (name, content[, mime]) tuples."""
    parts = []
    for name, content, *mime in files:
        parts.append(("file", (name, content, mime[0] if mime else "application/pdf")))
    return parts


def upload(client, headers, process, *files):
    return client.post(
        f"/api/processes/{process['id']}/documents", files=files_of(*files), headers=headers
    )


def upload_one(client, headers, process, label="um", name=None):
    """Upload one valid PDF and return its document JSON."""
    response = upload(client, headers, process, (name or f"{label}.pdf", pdf(label)))
    assert response.status_code == 201, response.text
    [result] = response.json()
    assert result["status_code"] == 201
    return result["document"]


def sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def seed_document(uow_factory, process, user, **fields):
    """Insert a document row directly (no file) and return the entity."""
    document = make_document(SimpleNamespace(id=uuid.UUID(process["id"])), user.id, **fields)
    with uow_factory() as uow:
        uow.documents.add(document)
        uow.commit()
    return document


def seed_run(uow_factory, document, texts=("Primeira pagina", "Segunda pagina"), **fields):
    run = make_run(
        document.id,
        created_at=datetime(2026, 11, 17, 9, 1, tzinfo=UTC),
        **fields,
    )
    pages = [
        PageText(
            document.id,
            run.id,
            number,
            TextMethod.OCR if number % 2 == 0 else TextMethod.TEXTO,
            len(text),
            Decimal("88.50") if number % 2 == 0 else None,
            text,
        )
        for number, text in enumerate(texts, start=1)
    ]
    with uow_factory() as uow:
        uow.extractions.add_run(run)
        uow.extractions.replace_pages(document.id, pages)
        uow.commit()
    return run


def stored_files(tmp_path):
    root = tmp_path / "storage"
    return sorted(p for p in root.rglob("*") if p.is_file()) if root.exists() else []


def finish_processing(uow_factory, document, status=DocumentStatus.PROCESSADO):
    """What the worker leaves behind: the job of the document done, the document `status`.

    `document` is the JSON of the API.
    """
    moment = datetime(2026, 11, 16, 9, 5, tzinfo=UTC)
    document_id = uuid.UUID(document["id"])
    with uow_factory() as uow:
        job = uow.jobs.active_for_document(document_id)
        uow.jobs.finish(job.id, JobStatus.CONCLUIDA, moment)
        current = uow.documents.get(document_id)
        uow.documents.update(replace(current, status=status), current.version)
        uow.commit()
