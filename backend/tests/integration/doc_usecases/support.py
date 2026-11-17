"""Helpers shared by the document use case tests."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from functools import lru_cache

from app.application.use_cases.scoring import ActivityData
from app.domain.entities.activity import ActivitySource
from app.domain.entities.document import PageText, RunStatus, TextMethod
from app.domain.repositories.ports import ActivityEvidence
from tests.integration.documents.factories import make_run
from tests.support import synthetic_docs as synth


@lru_cache
def pdf(label: str, pages: int = 1) -> bytes:
    """A valid PDF that differs from every other label; the same label gives the same bytes."""
    return synth.pdf_with_text([f"Documento ficticio numero {label}"] * pages)


def seed_run(
    world,
    document,
    texts=("Texto da pagina um", "Texto da pagina dois"),
    status=RunStatus.ATIVA,
    raw_json=None,
    warnings=(),
    model="fake-model",
    created_at=None,
):
    """Store an extraction run and its pages (as the processing does); returns the run."""
    run = make_run(
        document.id,
        status=status,
        raw_json=raw_json if raw_json is not None else {"activities": []},
        warnings=tuple(warnings),
        model=model,
        created_at=created_at or datetime(2026, 11, 17, 9, 1, tzinfo=UTC),
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
    with world.uow_factory() as uow:
        uow.extractions.add_run(run)
        if status is RunStatus.ATIVA:
            uow.extractions.replace_pages(document.id, pages)
        uow.commit()
    return run


def draft_activity(world, process, title="Atividade sugerida", **fields):
    """An AI-suggested draft activity created through the scoring use case."""
    data = ActivityData(title=title, group_number=3, item_number=4, **fields)
    return world.create.execute(world.admin, process.id, data, source=ActivitySource.SUGERIDA_IA)


def link(world, activity, document, page=1, excerpt="trecho", run_id=None, by=None):
    evidence = ActivityEvidence(
        id=uuid.uuid4(),
        activity_id=activity.id,
        document_id=document.id,
        page_number=page,
        excerpt=excerpt,
        created_by=(by or world.admin).id,
        run_id=run_id,
    )
    with world.uow_factory() as uow:
        uow.evidences.add(evidence)
        uow.commit()
    return evidence
