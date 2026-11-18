"""Builders for the generated-document repository tests."""

import uuid
from datetime import UTC, datetime

from app.domain.entities.generated import (
    DocumentFormat,
    DocumentKind,
    GeneratedDocument,
    GeneratedFile,
    GenerationState,
    WordingJob,
)

T0 = datetime(2026, 11, 18, 9, 0, tzinfo=UTC)


def make_generation(process, user_id, kind=DocumentKind.TABELA, **kwargs) -> GeneratedDocument:
    data = dict(
        id=uuid.uuid4(),
        process_id=process.id,
        kind=kind,
        state=GenerationState.GERANDO,
        version_number=None,
        requested_by=user_id,
        requested_at=T0,
    )
    data.update(kwargs)
    return GeneratedDocument(**data)


def make_file(fmt=DocumentFormat.PDF, size=2048) -> GeneratedFile:
    return GeneratedFile(fmt, f"{uuid.uuid4().hex}.{fmt.value.lower()}", "e" * 64, size)


def make_wording_job(process, user_id, section_key="1.1", **kwargs) -> WordingJob:
    data = dict(
        id=uuid.uuid4(),
        process_id=process.id,
        section_key=section_key,
        state=GenerationState.GERANDO,
        requested_by=user_id,
        requested_at=T0,
    )
    data.update(kwargs)
    return WordingJob(**data)
