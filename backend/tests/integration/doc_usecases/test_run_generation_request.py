"""REQ-01, REQ-04, REQ-05, REQ-06, REQ-08, PAR-14: running the generation of the Requerimento."""

import dataclasses
from datetime import date

import pymupdf
from docx import Document

from app.domain.entities.generated import DocumentFormat, DocumentKind, GenerationState
from tests.integration.doc_usecases.board_support import add_typed_ordinance
from tests.integration.doc_usecases.opinion_support import (
    add_city,
    add_opinion,
    ask,
    ready,
    ready_table,
)

PROMOTION = {
    "current_class": "B",
    "current_denomination": "Adjunto",
    "current_level": 4,
    "target_class": "C",
    "target_denomination": "Associado",
    "target_level": 1,
}
BLANK_EVALUATION = "realizada na data de ___/___/___."


def a_promotion_from_b4_to_c1(gen):
    with gen.world.uow_factory() as uow:
        current = uow.processes.get(gen.world.process.id)
        uow.processes.update(dataclasses.replace(current, **PROMOTION), current.version)
        uow.commit()


def file_path(gen, generation, fmt):
    [found] = [f for f in generation.files if f.format is fmt]
    return gen.generated.path(generation.process_id, found.internal_name)


def texts(gen, generation) -> dict[DocumentFormat, str]:
    """The text of each file with every run of white space as one space."""
    docx = " ".join(
        p.text for p in Document(str(file_path(gen, generation, DocumentFormat.DOCX))).paragraphs
    )
    with pymupdf.open(file_path(gen, generation, DocumentFormat.PDF)) as pdf:
        pdf_text = " ".join(page.get_text() for page in pdf)
    return {
        DocumentFormat.DOCX: " ".join(docx.split()),
        DocumentFormat.PDF: " ".join(pdf_text.split()),
    }


def request(gen):
    return ready(gen, DocumentKind.REQUERIMENTO)


# --- a process with nothing but the data of Stage 1 ---------------------------------------------


def test_with_no_activity_no_table_and_no_parecer_the_run_stores_version_1_with_both_files(gen):
    a_promotion_from_b4_to_c1(gen)
    add_city(gen.world, "Belém")

    generation = request(gen)

    assert (generation.kind, generation.state, generation.version_number) == (
        DocumentKind.REQUERIMENTO,
        GenerationState.PRONTO,
        1,
    )
    assert sorted(f.format for f in generation.files) == [DocumentFormat.DOCX, DocumentFormat.PDF]
    for fmt, text in texts(gen, generation).items():
        assert "Prezado Sr. Presidente da CPPD," in text, fmt
        assert "(X) Magistério Superior" in text, fmt
        assert (
            "solicito promoção funcional, do nível 4 da classe B (Adjunto) para o nível 1 da "
            "classe C (Associado), referente ao interstício 23/11/2022 a 23/11/2024."
        ) in text, fmt
        assert "Belém, 10 de março de 2025." in text, fmt
        assert BLANK_EVALUATION in text, fmt


def test_without_a_city_the_closing_line_starts_with_a_blank(gen):
    a_promotion_from_b4_to_c1(gen)

    generation = request(gen)

    for fmt, text in texts(gen, generation).items():
        assert "__________, 10 de março de 2025." in text, fmt
    assert generation.snapshot["city"] is None


def test_after_a_parecer_the_evaluation_line_has_its_date(gen):
    a_promotion_from_b4_to_c1(gen)
    ready_table(gen)
    add_typed_ordinance(gen.world)
    add_opinion(gen.world, when=date(2024, 12, 5))
    parecer = ready(gen, DocumentKind.PARECER)

    generation = request(gen)

    for fmt, text in texts(gen, generation).items():
        assert "realizada na data de 05/12/2024." in text, fmt
        assert BLANK_EVALUATION not in text
    assert generation.snapshot["opinion_date"] == "2024-12-05"
    assert generation.snapshot["opinion_version"] == parecer.version_number == 1


def test_a_parecer_with_no_date_leaves_the_evaluation_line_blank(gen):
    ready_table(gen)
    add_typed_ordinance(gen.world)
    add_opinion(gen.world, when=None)
    ready(gen, DocumentKind.PARECER)

    generation = request(gen)

    for fmt, text in texts(gen, generation).items():
        assert BLANK_EVALUATION in text, fmt
    assert generation.snapshot["opinion_date"] is None
    assert generation.snapshot["opinion_version"] == 1


def test_a_parecer_that_is_only_generating_does_not_give_its_date(gen):
    ready_table(gen)
    add_typed_ordinance(gen.world)
    add_opinion(gen.world, when=date(2024, 12, 5))
    parecer = ask(gen, DocumentKind.PARECER)
    with gen.world.uow_factory() as uow:  # started and never finished: still GERANDO
        assert uow.generations.claim_next(gen.clock.now()).id == parecer.id
        uow.commit()

    generation = request(gen)

    for text in texts(gen, generation).values():
        assert BLANK_EVALUATION in text
    assert generation.snapshot["opinion_version"] is None


# --- the snapshot -------------------------------------------------------------------------------


def test_the_snapshot_keeps_the_filled_fields_the_city_and_the_dates_used(gen):
    a_promotion_from_b4_to_c1(gen)
    add_city(gen.world, "Belém")

    snapshot = request(gen).snapshot

    assert snapshot["city"] == "Belém"
    assert snapshot["opening_date"] == "2025-03-10"
    assert snapshot["career"] == "MAGISTERIO_SUPERIOR"
    assert snapshot["modality"] == "PROMOCAO"
    assert snapshot["interstice"] == {"start": "2022-11-23", "end": "2024-11-23"}
    assert snapshot["current"] == {"class": "B", "level": 4, "denomination": "Adjunto"}
    assert snapshot["target"] == {"class": "C", "level": 1, "denomination": "Associado"}


# --- again, history (PAR-14) --------------------------------------------------------------------


def test_asking_again_makes_version_2_and_version_1_stays_untouched(gen):
    a_promotion_from_b4_to_c1(gen)
    add_city(gen.world, "Belém")
    first = request(gen)
    before = {fmt: file_path(gen, first, fmt).read_bytes() for fmt in DocumentFormat}

    second = request(gen)

    assert (first.version_number, second.version_number) == (1, 2)
    with gen.world.uow_factory() as uow:
        history = uow.generations.list_for_process(gen.world.process.id, DocumentKind.REQUERIMENTO)
    assert sorted(g.version_number for g in history if g.state is GenerationState.PRONTO) == [1, 2]
    for fmt in DocumentFormat:
        assert file_path(gen, first, fmt).read_bytes() == before[fmt]


# --- no AI (REQ-08) -----------------------------------------------------------------------------


def test_the_requerimento_is_made_without_calling_the_ai(gen, no_ai):
    generation = request(gen)

    assert generation.state is GenerationState.PRONTO
    assert no_ai == []
