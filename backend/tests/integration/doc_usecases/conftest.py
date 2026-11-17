"""Fixtures for the document use cases: real storage in a temp dir, real file inspector,
synthetic files and a clock the test can move."""

import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.application.services.audit_service import AuditService
from app.application.use_cases import documents
from app.infrastructure.files.inspector import PillowFileInspector
from app.infrastructure.storage.local_storage import LocalFileStorage
from tests.integration.documents.factories import make_document
from tests.integration.scoring.conftest import add_process, world  # noqa: F401  (fixtures)

START = datetime(2026, 11, 17, 9, 0, tzinfo=UTC)


class MovableClock:
    def __init__(self) -> None:
        self.moment = START

    def now(self) -> datetime:
        return self.moment

    def advance(self, **kwargs) -> None:
        self.moment += timedelta(**kwargs)


@pytest.fixture
def docs(world, tmp_path):  # noqa: F811
    """World of the scoring tests plus the document use cases bound to temp storage."""
    clock = MovableClock()
    audit = AuditService(clock)
    storage = LocalFileStorage(tmp_path / "storage")
    inspector = PillowFileInspector()
    incoming_dir = tmp_path / "incoming"
    incoming_dir.mkdir()

    def incoming(content: bytes, name: str = "declaracao.pdf", mime: str | None = None):
        path = incoming_dir / uuid.uuid4().hex
        path.write_bytes(content)
        if mime is None:
            mime = "application/pdf" if name.lower().endswith(".pdf") else None
        return documents.IncomingFile(
            path, name, mime, len(content), hashlib.sha256(content).hexdigest()
        )

    def add_documents(process, user, count, **kwargs):
        """Insert documents directly (no file), as uploaded at the clock moment by default."""
        with world.uow_factory() as uow:
            for _ in range(count):
                fields = {"uploaded_at": clock.now()} | kwargs
                uow.documents.add(make_document(process, user.id, **fields))
            uow.commit()

    def upload_one(actor, process, content: bytes, name: str = "declaracao.pdf"):
        """Upload one valid file through the use case and return the stored document."""
        [result] = upload.execute(actor, process.id, [incoming(content, name)])
        assert result.status_code == 201, result
        return result.document

    def upload_uc(limits=None, uow_factory=None):
        return documents.UploadDocuments(
            uow_factory or world.uow_factory, audit, world.policy, storage, inspector, clock, limits
        )

    upload = upload_uc()

    def manage(use_case, uow_factory=None, limits=None):
        """A replace/reprocess use case bound to the same storage, inspector and clock."""
        return use_case(
            uow_factory or world.uow_factory,
            audit,
            world.policy,
            storage,
            inspector,
            clock,
            world.change_status,
            limits,
        )

    return SimpleNamespace(
        world=world,
        clock=clock,
        audit=audit,
        storage=storage,
        inspector=inspector,
        storage_root=tmp_path / "storage",
        incoming=incoming,
        add_documents=add_documents,
        upload=upload,
        upload_one=upload_one,
        upload_with=upload_uc,
        replace=manage(documents.ReplaceDocument),
        replace_with=lambda **kw: manage(documents.ReplaceDocument, **kw),
        delete=documents.DeleteDocument(world.uow_factory, audit, world.policy, storage),
        reprocess=documents.ReprocessDocument(
            world.uow_factory, audit, world.policy, world.change_status
        ),
        classify=documents.ClassifyDocumentManually(world.uow_factory, audit, world.policy),
    )


@pytest.fixture
def stored_files(docs):
    """Every file under the storage root."""
    return lambda: sorted(p for p in Path(docs.storage_root).rglob("*") if p.is_file())
