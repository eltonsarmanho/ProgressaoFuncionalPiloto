"""Builders for the generation use case tests: activities, documents and page links inserted
straight in the database, with made-up names only."""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.application.use_cases.generated_documents import (
    GenerationLimits,
    RequestGeneration,
    RunGeneration,
)
from app.application.use_cases.scoring import ActivityData
from app.domain.entities.activity import Activity, ActivityStatus, Level
from app.domain.entities.document import DocAlertCode
from app.domain.repositories.ports import ActivityEvidence
from app.infrastructure.documents.config_loader import ReportConfigLoader
from app.infrastructure.documents.document_writer import FileDocumentWriter
from app.infrastructure.documents.front_matter import TOC_CAPACITY
from app.infrastructure.storage.generated_storage import LocalGeneratedStorage
from tests.integration.documents.factories import make_document

MOMENT = datetime(2026, 11, 18, 9, 0, tzinfo=UTC)


def add_activity(world, process=None, **kwargs) -> Activity:
    """A validated activity of group II item 7, dated inside the interstice, unless told."""
    process = process or world.process
    fields = dict(
        id=uuid.uuid4(),
        process_id=process.id,
        title=f"Atividade {uuid.uuid4().hex[:6]}",
        created_by=world.admin.id,
        group_number=2,
        item_number=7,
        event_date=date(2023, 5, 10),
        quantity=Decimal("1"),
        status=ActivityStatus.VALIDADA,
        created_at=MOMENT,
    )
    fields.update(kwargs)
    activity = Activity(**fields)
    with world.uow_factory() as uow:
        uow.activities.add(activity)
        uow.commit()
    return activity


def add_document(world, process=None, **kwargs):
    """A document row of the process (no file); `outside=True` marks it as out of the interstice."""
    process = process or world.process
    if kwargs.pop("outside", False):
        kwargs["status_code"] = DocAlertCode.DOCUMENTO_FORA_DO_INTERSTICIO.value
    document = make_document(process, world.admin.id, **kwargs)
    with world.uow_factory() as uow:
        uow.documents.add(document)
        uow.commit()
    return document


def link(world, activity, document, page=1) -> ActivityEvidence:
    evidence = ActivityEvidence(
        id=uuid.uuid4(),
        activity_id=activity.id,
        document_id=document.id,
        page_number=page,
        excerpt="trecho",
        created_by=world.admin.id,
    )
    with world.uow_factory() as uow:
        uow.evidences.add(evidence)
        uow.commit()
    return evidence


def build_request(world, docs, storage=None, limits=None) -> RequestGeneration:
    return RequestGeneration(
        world.uow_factory,
        world.audit,
        world.policy,
        docs.clock,
        storage or LocalGeneratedStorage(docs.storage_root),
        docs.storage,
        docs.inspector,
        limits or GenerationLimits(),
        TOC_CAPACITY,
    )


def build_run(world, docs, **overrides) -> RunGeneration:
    deps = dict(
        uow_factory=world.uow_factory,
        audit=world.audit,
        clock=docs.clock,
        storage=LocalGeneratedStorage(docs.storage_root),
        writer=FileDocumentWriter(),
        report_config=ReportConfigLoader(),
        toc_capacity=TOC_CAPACITY,
    )
    return RunGeneration(**(deps | overrides))


@pytest.fixture
def gen(docs, official_chosen):
    """The world of the document tests with the official table chosen, plus the generation use
    cases bound to temporary storage."""
    world = official_chosen
    return SimpleNamespace(
        world=world,
        docs=docs,
        clock=docs.clock,
        originals=docs.storage,
        generated=LocalGeneratedStorage(docs.storage_root),
        request=lambda storage=None, limits=None: build_request(world, docs, storage, limits),
        run=lambda **overrides: build_run(world, docs, **overrides),
    )


def store_original(gen, process, content: bytes, ext: str = "pdf", **kwargs):
    """A document row whose file is really in the originals storage."""
    name = gen.originals.save(process.id, ext, content)
    mime = {"pdf": "application/pdf", "png": "image/png", "jpg": "image/jpeg"}[ext]
    return add_document(gen.world, process, internal_name=name, mime=mime, **kwargs)


def link_pages(world, activity, document, pages) -> None:
    """Links of several pages of one document to the activity, in one commit."""
    with world.uow_factory() as uow:
        for page in pages:
            uow.evidences.add(
                ActivityEvidence(
                    id=uuid.uuid4(),
                    activity_id=activity.id,
                    document_id=document.id,
                    page_number=page,
                    excerpt="trecho",
                    created_by=world.admin.id,
                )
            )
        uow.commit()


def add_scenario_211(world) -> None:
    """The activities of the acceptance scenario of the official table (tabela-oficial, ACE-01):
    subtotals II to VIII of 52, 7, 62, 0, 30, 4 and 56, total 211, PIT hours 24, 24, 24 and 20."""
    def create(**kwargs):
        world.create.execute(
            world.admin, world.process.id, ActivityData(evidence_note="Declaração", **kwargs)
        )

    semesters = [("2023.1", date(2023, 3, 6)), ("2023.2", date(2023, 8, 7)),
                 ("2023.3", date(2023, 12, 4)), ("2023.4", date(2024, 3, 4))]  # fmt: skip
    offers = [(68, 68, 68), (68, 68, 68), (68, 68, 68), (68, 68, 34)]
    for (period, day), hours in zip(semesters, offers, strict=True):
        for number, offer_hours in enumerate(hours, start=1):
            create(
                title=f"Disciplina {number} {period}", group_number=1, event_date=day,
                academic_period=period, level=Level.GRADUACAO, hours=Decimal(offer_hours),
            )  # fmt: skip
    for group, item, times in [(2, 7, 4), (2, 8, 4), (2, 12, 4), (4, 1, 4), (7, 10, 2)]:
        for n in range(1, times + 1):
            create(
                title=f"Item {group}.{item} número {n}", group_number=group, item_number=item,
                quantity=Decimal(1), event_date=date(2023, n + 3, 15),
            )  # fmt: skip
    for group, item in [(3, 2), (3, 3), (6, 6), (8, 9), (8, 10), (8, 11), (8, 36)]:
        create(
            title=f"Item {group}.{item}", group_number=group, item_number=item,
            quantity=Decimal(1), event_date=date(2024, 2, 20),
        )  # fmt: skip
    create(
        title="Curso de extensão ministrado", group_number=4, item_number=4, quantity=Decimal(1),
        hours=Decimal(21), event_date=date(2024, 5, 10),
    )  # fmt: skip
