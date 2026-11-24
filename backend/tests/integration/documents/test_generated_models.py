"""VER-02, REL-13: each ORM model of the generated documents writes and reads a row."""

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.domain.entities.generated import DocumentFormat, DocumentKind, GenerationState
from app.infrastructure.database.models import (
    ComprovanteLayoutModel,
    DocumentModel,
    GeneratedDocumentModel,
    GeneratedFileModel,
    ReportDraftModel,
    ReportWordingJobModel,
)
from tests.integration.documents.test_schema import insert_document

REQUESTED_AT = datetime(2026, 11, 18, 9, 0, tzinfo=UTC)
FINISHED_AT = datetime(2026, 11, 18, 9, 1, tzinfo=UTC)


def _round_trip(engine, model):
    """Writes the model in one session and reads it back, by primary key, in another."""
    with Session(engine) as session:
        session.add(model)
        session.commit()
        key = model.id
    with Session(engine) as session:
        return session.get(type(model), key)


def test_a_generated_document_keeps_its_enums_version_snapshot_and_alerts(engine, process, base):
    generation = GeneratedDocumentModel(
        id=uuid.uuid4(),
        process_id=process.id,
        kind=DocumentKind.RELATORIO,
        state=GenerationState.PRONTO,
        version_number=2,
        requested_by=base["admin"].id,
        requested_at=REQUESTED_AT,
        started_at=REQUESTED_AT,
        finished_at=FINISHED_AT,
        snapshot={"total": "211.00", "activities": []},
        alerts=[{"code": "ATIVIDADE_SEM_COMPROVANTE", "message": "sem página"}],
        plan_hash="a" * 64,
    )

    loaded = _round_trip(engine, generation)

    assert loaded.kind is DocumentKind.RELATORIO
    assert loaded.state is GenerationState.PRONTO
    assert loaded.version_number == 2
    assert loaded.snapshot == {"total": "211.00", "activities": []}
    assert loaded.alerts == [{"code": "ATIVIDADE_SEM_COMPROVANTE", "message": "sem página"}]
    assert (loaded.plan_hash, loaded.finished_at) == ("a" * 64, FINISHED_AT)


def test_a_generated_file_keeps_its_format_hash_and_size(engine, process, base):
    generation = GeneratedDocumentModel(
        id=uuid.uuid4(),
        process_id=process.id,
        kind=DocumentKind.TABELA,
        state=GenerationState.GERANDO,
        requested_by=base["admin"].id,
    )
    _round_trip(engine, generation)
    file = GeneratedFileModel(
        id=uuid.uuid4(),
        generated_document_id=generation.id,
        format=DocumentFormat.DOCX,
        internal_name="abc.docx",
        sha256="b" * 64,
        size_bytes=5_000_000_000,
    )

    loaded = _round_trip(engine, file)

    assert loaded.format is DocumentFormat.DOCX
    assert (loaded.internal_name, loaded.sha256) == ("abc.docx", "b" * 64)
    assert loaded.size_bytes == 5_000_000_000
    assert loaded.created_at is not None


def test_a_wording_job_keeps_its_section_state_and_warnings(engine, process, base):
    job = ReportWordingJobModel(
        id=uuid.uuid4(),
        process_id=process.id,
        section_key="1.2",
        state=GenerationState.PRONTO,
        requested_by=base["admin"].id,
        requested_at=REQUESTED_AT,
        warnings=[{"code": "REDACAO_REJEITADA", "reason": "NUMERO,DATA"}],
    )

    loaded = _round_trip(engine, job)

    assert (loaded.section_key, loaded.state) == ("1.2", GenerationState.PRONTO)
    assert loaded.warnings == [{"code": "REDACAO_REJEITADA", "reason": "NUMERO,DATA"}]
    assert loaded.error_code is None


def test_a_report_draft_keeps_its_content_version_and_authors(engine, process, base):
    content = {"sections": [{"key": "1.1", "entries": []}]}
    draft = ReportDraftModel(
        id=uuid.uuid4(),
        process_id=process.id,
        template_id="ufpa-cppd",
        template_version=3,
        content=content,
        version=1,
        created_by=base["admin"].id,
        updated_by=base["admin"].id,
    )

    loaded = _round_trip(engine, draft)

    assert loaded.content == content
    assert (loaded.template_id, loaded.template_version, loaded.version) == ("ufpa-cppd", 3, 1)
    assert loaded.created_by == loaded.updated_by == base["admin"].id
    assert loaded.updated_at is not None


def test_a_comprovante_layout_keeps_its_content_and_version(engine, process, base):
    content = {"activities": [], "base_evidence_keys": []}
    layout = ComprovanteLayoutModel(
        id=uuid.uuid4(),
        process_id=process.id,
        content=content,
        version=4,
        updated_by=base["admin"].id,
    )

    loaded = _round_trip(engine, layout)

    assert loaded.content == content
    assert loaded.version == 4
    assert loaded.updated_at is not None


def test_a_document_keeps_the_file_deleted_at_mark(engine, process, base):
    with engine.begin() as conn:
        document_id = insert_document(conn, process, base["admin"].id)
    with Session(engine) as session:
        document = session.get(DocumentModel, document_id)
        assert document.file_deleted_at is None
        document.file_deleted_at = FINISHED_AT
        session.commit()

    with Session(engine) as session:
        assert session.get(DocumentModel, document_id).file_deleted_at == FINISHED_AT
