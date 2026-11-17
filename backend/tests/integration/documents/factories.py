"""Builders for document-related entities."""

import uuid
from datetime import UTC, datetime

from app.domain.entities.document import Document, ExtractionRun


def make_document(process, user_id, **kwargs) -> Document:
    data = dict(
        id=uuid.uuid4(),
        process_id=process.id,
        original_name="declaracao.pdf",
        internal_name=f"{uuid.uuid4().hex}.pdf",
        mime="application/pdf",
        size_bytes=1234,
        sha256=uuid.uuid4().hex + uuid.uuid4().hex,
        page_count=2,
        uploaded_by=user_id,
        uploaded_at=datetime(2026, 11, 17, 9, 0, tzinfo=UTC),
    )
    data.update(kwargs)
    return Document(**data)


def make_run(document_id, **kwargs) -> ExtractionRun:
    data = dict(
        id=uuid.uuid4(),
        document_id=document_id,
        model="sabia-4-br-sp",
        duration_ms=1500,
        raw_json={"activities": []},
        warnings=("TRUNCADO",),
        created_at=datetime(2026, 11, 17, 9, 1, tzinfo=UTC),
    )
    data.update(kwargs)
    return ExtractionRun(**data)
