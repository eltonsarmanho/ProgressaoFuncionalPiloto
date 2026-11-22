"""Builders for the conclusion tests: input documents with a real file, extracted pages and a link
from an activity, in synthetic data only."""

import uuid
from datetime import date
from pathlib import Path
from types import SimpleNamespace

from app.domain.entities.board import BoardOrdinance, OrdinanceFile, ReadingState, ValueSource
from app.domain.entities.document import PageText, TextMethod
from app.domain.entities.generated import (
    ARTIFACT_KINDS,
    DocumentFormat,
    GeneratedFile,
    GenerationCode,
    GenerationState,
)
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
    for kind in ARTIFACT_KINDS:
        add_generation(world, kind, process=process)


def add_stored_generation(gen, kind, content=b"gerado"):
    """A PRONTO version of the kind whose PDF really is in the generated storage; returns the
    internal name and the content."""
    world = gen.world
    temp = gen.generated.new_temp_path(world.process.id)
    temp.write_bytes(content)
    name = gen.generated.commit(world.process.id, temp, "pdf")
    generation = make_generation(world.process, world.admin.id, kind)
    with world.uow_factory() as uow:
        uow.generations.add(generation)
        uow.generations.finish_ready(
            generation.id,
            T0,
            [GeneratedFile(DocumentFormat.PDF, name, "a" * 64, len(content))],
            {"total": "1"},
            (),
        )
        uow.commit()
    return name, content


def add_ordinance(gen, process=None, size=None, members=(), state=ReadingState.LIDA, stored=True):
    """The ordinance of the process with a typed number and date. With `stored` its file really is
    in the originals storage (`size` is the size the row declares); without it the ordinance has
    only the typed data. Returns the file (or None) and the ordinance."""
    world = gen.world
    process = process or world.process
    file = None
    if stored:
        content = CONTENT + uuid.uuid4().hex.encode()
        name = gen.originals.save(process.id, "pdf", content)
        file = OrdinanceFile(
            name, "portaria.pdf", "application/pdf", size or len(content), "f" * 64, 1
        )
    ordinance = BoardOrdinance(
        process.id,
        number="77/2025",
        number_source=ValueSource.INFORMADO,
        ordinance_date=date(2025, 3, 10),
        date_source=ValueSource.INFORMADO,
        members=tuple(members),
        file=file,
        reading_state=state if stored else ReadingState.SEM_ARQUIVO,
    )
    with world.uow_factory() as uow:
        saved = uow.board.create(ordinance, world.admin.id, 0)
        uow.commit()
    return file, saved
