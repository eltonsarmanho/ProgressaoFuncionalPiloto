"""Builders for the generated-document repository tests."""

import uuid
from datetime import UTC, datetime

from app.domain.entities.comprovante import (
    ComprovanteLayout,
    EvidenceKey,
    LayoutActivity,
    LayoutPage,
)
from app.domain.entities.generated import (
    DocumentFormat,
    DocumentKind,
    GeneratedDocument,
    GeneratedFile,
    GenerationState,
    WordingJob,
)
from app.domain.entities.report import DraftEntry, DraftSection, EntrySource, ReportDraft

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


def make_draft(process, sections=None, version=0) -> ReportDraft:
    if sections is None:
        sections = (
            DraftSection(
                "1.1",
                "Ensino",
                entries=(
                    DraftEntry(uuid.uuid4(), "Aula A", EntrySource.MODELO),
                    DraftEntry(uuid.uuid4(), "Aula B", EntrySource.MODELO),
                ),
            ),
            DraftSection(
                "1.2",
                "Pesquisa",
                free_text="Texto livre",
                entries=(DraftEntry(uuid.uuid4(), "Projeto", EntrySource.MODELO),),
            ),
        )
    return ReportDraft(process.id, "ufpa-cppd", 1, tuple(sections), version)


def make_layout(process, version=0) -> ComprovanteLayout:
    first, second = uuid.uuid4(), uuid.uuid4()
    doc_a, doc_b = uuid.uuid4(), uuid.uuid4()
    return ComprovanteLayout(
        process.id,
        (
            LayoutActivity(
                first,
                (LayoutPage(doc_a, 1), LayoutPage(doc_b, 3, "mesma página, outro curso")),
                group_number=1,
                item_number=1,
            ),
            LayoutActivity(second, (LayoutPage(doc_a, 2),), group_number=2, item_number=3),
        ),
        (EvidenceKey(first, doc_a, 1), EvidenceKey(second, doc_a, 2)),
        version,
    )
