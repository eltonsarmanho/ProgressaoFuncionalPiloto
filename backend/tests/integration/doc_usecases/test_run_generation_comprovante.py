"""CMP-01, CMP-02, CMP-04, CMP-05, CMP-07, VER-02: running the generation of the Comprovante."""

from dataclasses import replace

import pymupdf

from app.application.services.generation_inputs import load_generation_inputs
from app.domain.entities.generated import (
    DocumentFormat,
    DocumentKind,
    GenerationAlertCode,
    GenerationState,
)
from app.domain.rules.comprovante_plan import plan_comprovante
from tests.integration.doc_usecases.generation_support import (
    TOC_CAPACITY,
    add_activity,
    add_document,
    link,
    store_original,
)
from tests.integration.doc_usecases.test_run_generation_table import file_of, generate
from tests.support import synthetic_docs as synth


def original(gen, label="Alfa", pages=3):
    return store_original(
        gen,
        gen.world.process,
        synth.pdf_with_text([f"{label} pagina {n}" for n in range(1, pages + 1)]),
        page_count=pages,
    )


def current_plan(world):
    with world.uow_factory() as uow:
        inputs = load_generation_inputs(uow, uow.processes.get(world.process.id))
    return inputs, plan_comprovante(inputs.layout, inputs.activities, TOC_CAPACITY)


def pages_of(gen, done):
    with pymupdf.open(file_of(gen, done, DocumentFormat.PDF)[1]) as pdf:
        return [page.get_text() for page in pdf]


def three_activities(gen):
    """A and B have a page each of one document, C has none."""
    world = gen.world
    first = add_activity(world, title="Atividade A", item_number=7)
    second = add_activity(world, title="Atividade B", item_number=8)
    add_activity(world, title="Atividade C", item_number=12)
    document = original(gen)
    link(world, first, document, 1)
    link(world, second, document, 3)
    return document


def test_the_pdf_has_the_pages_and_the_numbers_of_the_plan_and_the_hash_in_the_snapshot(gen):
    three_activities(gen)

    done = generate(gen, DocumentKind.COMPROVANTE)

    _, plan = current_plan(gen.world)
    assert done.state is GenerationState.PRONTO
    assert [f.format for f in done.files] == [DocumentFormat.PDF]
    pages = pages_of(gen, done)
    assert len(pages) == len(plan.pages)
    originals = [p for p in plan.pages if p.document_id is not None]
    assert [p.number for p in originals] == [4, 5]
    assert "Alfa pagina 1" in pages[3] and "Comprovante p. 4" in pages[3]
    assert "Alfa pagina 3" in pages[4] and "Comprovante p. 5" in pages[4]
    assert done.plan_hash == plan.plan_hash == done.snapshot["layout"]["plan_hash"]


def test_an_activity_without_a_page_gives_the_alert_and_the_note(gen):
    three_activities(gen)

    done = generate(gen, DocumentKind.COMPROVANTE)

    [alert] = [a for a in done.alerts if a.code is GenerationAlertCode.ATIVIDADE_SEM_COMPROVANTE]
    assert "Atividade C" in alert.message
    assert any("Sem comprovante anexado" in page for page in pages_of(gen, done))


def test_a_page_linked_only_to_a_document_outside_the_interstice_is_not_attached(gen):
    world = gen.world
    activity = add_activity(world, title="Atividade fora")
    outside = add_document(world, outside=True)  # it has no file: attaching it would fail
    link(world, activity, outside, 1)

    done = generate(gen, DocumentKind.COMPROVANTE)

    _, plan = current_plan(world)
    assert len(pages_of(gen, done)) == len(plan.pages) == 3  # cover, contents, separator
    assert [a.code for a in done.alerts] == [GenerationAlertCode.ATIVIDADE_SEM_COMPROVANTE]


def save_layout_without_the_page_of(world, activity_title):
    inputs, _ = current_plan(world)
    layout = replace(
        inputs.layout,
        activities=tuple(
            replace(e, pages=())
            if next(a.title for a in inputs.activities if a.id == e.activity_id) == activity_title
            else e
            for e in inputs.layout.activities
        ),
    )
    with world.uow_factory() as uow:
        uow.comprovante_layouts.create(layout, world.admin.id, 0)
        uow.commit()


def codes(done):
    return [a.code for a in done.alerts]


def test_the_table_has_no_layout_and_no_plan_hash_while_the_comprovante_keeps_both(gen):
    # GTAB-08: the table no longer cites the Comprovante, so it carries no arrangement
    three_activities(gen)

    table = generate(gen, DocumentKind.TABELA)
    comprovante = generate(gen, DocumentKind.COMPROVANTE)

    assert table.plan_hash is None
    assert "layout" not in table.snapshot
    assert comprovante.plan_hash == current_plan(gen.world)[1].plan_hash
    assert comprovante.snapshot["layout"]["plan_hash"] == comprovante.plan_hash
    assert GenerationAlertCode.NUMERACAO_DIVERGENTE not in codes(comprovante)
    assert GenerationAlertCode.NUMERACAO_DIVERGENTE not in codes(table)


def test_after_the_arrangement_changes_the_comprovante_does_not_warn_of_the_older_table(gen):
    three_activities(gen)
    generate(gen, DocumentKind.TABELA)
    save_layout_without_the_page_of(gen.world, "Atividade A")

    comprovante = generate(gen, DocumentKind.COMPROVANTE)

    assert GenerationAlertCode.NUMERACAO_DIVERGENTE not in codes(comprovante)
    assert comprovante.plan_hash is not None


def test_the_table_does_not_warn_when_the_latest_comprovante_was_numbered_differently(gen):
    three_activities(gen)
    comprovante = generate(gen, DocumentKind.COMPROVANTE)
    save_layout_without_the_page_of(gen.world, "Atividade A")

    table = generate(gen, DocumentKind.TABELA)

    assert table.plan_hash != comprovante.plan_hash
    assert GenerationAlertCode.NUMERACAO_DIVERGENTE not in codes(table)
