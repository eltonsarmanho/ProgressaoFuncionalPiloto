"""Builders for the conclusion tests: input documents with a real file, extracted pages and a link
from an activity, in synthetic data only."""

import uuid
from pathlib import Path
from types import SimpleNamespace

from app.domain.entities.document import PageText, TextMethod
from app.domain.entities.generated import DocumentKind, GenerationCode, GenerationState
from tests.integration.doc_usecases.generation_support import (
    add_activity,
    add_document,
    link,
)
from tests.integration.documents.factories import make_run
from tests.integration.documents.generated_support import T0, make_file, make_generation

CONTENT = b"%PDF-1.4 conteudo sintetico "


def add_input_document(gen, process=None, size=None, **kwargs):
    """A document with a real stored file, two pages of text and one link of an activity to its
    page 1 (excerpt `trecho`). Returns the document and the link."""
    world = gen.world
    process = process or world.process
    content = CONTENT + uuid.uuid4().hex.encode()
    internal_name = gen.originals.save(process.id, "pdf", content)
    document = add_document(
        world,
        process,
        internal_name=internal_name,
        size_bytes=size if size is not None else len(content),
        **kwargs,
    )
    run = make_run(document.id)
    with world.uow_factory() as uow:
        uow.extractions.add_run(run)
        uow.extractions.replace_pages(
            document.id,
            [
                PageText(document.id, run.id, n, TextMethod.TEXTO, 12, None, f"texto da pagina {n}")
                for n in (1, 2)
            ],
        )
        uow.commit()
    evidence = link(world, add_activity(world, process), document, page=1)
    return document, evidence


def file_of(gen, document) -> Path:
    return gen.originals.path(document.process_id, document.internal_name)


def state_of(gen, document) -> SimpleNamespace:
    """What is stored about the document now: the row, the page numbers and the links."""
    with gen.world.uow_factory() as uow:
        evidences = uow.evidences.list_for_document(document.id)
        return SimpleNamespace(
            row=uow.documents.get(document.id),
            pages=[p.page_number for p in uow.extractions.list_pages(document.id)],
            links=[(e.page_number, e.excerpt) for e in evidences],
            file_exists=file_of(gen, document).exists(),
        )


def add_generation(world, kind, state=GenerationState.PRONTO, process=None):
    """A version of the kind in the given state: PRONTO gets a number and a file."""
    process = process or world.process
    generation = make_generation(process, world.admin.id, kind)
    with world.uow_factory() as uow:
        uow.generations.add(generation)
        if state is GenerationState.PRONTO:
            uow.generations.finish_ready(generation.id, T0, [make_file()], {"total": "1"}, ())
        elif state is GenerationState.FALHOU:
            uow.generations.finish_failed(generation.id, T0, GenerationCode.ERRO_INTERNO, "erro")
        uow.commit()
    return generation


def add_all_ready(world, process=None) -> None:
    for kind in DocumentKind:
        add_generation(world, kind, process=process)
