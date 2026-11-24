"""PAR-02, PAR-10, PAR-14, VER-08, PMOD-02, PMOD-03, PMOD-19, PMOD-20, PMOD-24, PMOD-25: running
the generation of the Parecer, with the text of the official model."""

import dataclasses
import zipfile

import pymupdf
from docx import Document

from app.application.use_cases.generated_documents import RecoverInterruptedGenerations
from app.domain.entities.board import BoardOpinion, OpinionConclusion
from app.domain.entities.generated import (
    DocumentFormat,
    DocumentKind,
    GenerationCode,
    GenerationState,
)
from tests.integration.doc_usecases.board_support import MEMBERS, add_typed_ordinance
from tests.integration.doc_usecases.generation_support import add_activity, add_scenario_211
from tests.integration.doc_usecases.opinion_support import (
    add_opinion,
    ask,
    craft_ready_table,
    ready,
    ready_table,
    run_one,
)

OUTDATED_MESSAGE = "A pontuação mudou depois da última Tabela; gere a Tabela de novo"


def stored_files(gen):
    root = gen.docs.storage_root / "generated"
    return sorted(p.name for p in root.rglob("*") if p.is_file())


def file_path(gen, generation, fmt):
    [found] = [f for f in generation.files if f.format is fmt]
    return gen.generated.path(generation.process_id, found.internal_name)


def docx_text(path) -> str:
    document = Document(str(path))
    cells = [c.text for t in document.tables for r in t.rows for c in r.cells]
    return "\n".join([p.text for p in document.paragraphs] + cells)


def pdf_text(path) -> str:
    with pymupdf.open(path) as pdf:
        return "\n".join(page.get_text() for page in pdf)


def texts(gen, generation) -> dict[DocumentFormat, str]:
    return {
        DocumentFormat.DOCX: docx_text(file_path(gen, generation, DocumentFormat.DOCX)),
        DocumentFormat.PDF: pdf_text(file_path(gen, generation, DocumentFormat.PDF)),
    }


def flat(text: str) -> str:
    return " ".join(text.split())


def flat_texts(gen, generation) -> dict[DocumentFormat, str]:
    return {fmt: flat(text) for fmt, text in texts(gen, generation).items()}


def board(gen, conclusion=OpinionConclusion.FAVORAVEL):
    add_typed_ordinance(gen.world)
    add_opinion(gen.world, conclusion=conclusion)


def a_ready_parecer(gen):
    """A Tabela, three members and the conclusion; returns the Tabela and the Parecer rows."""
    table = ready_table(gen)
    board(gen)
    return table, ready(gen, DocumentKind.PARECER)


def run_row(gen, generation_id):
    with gen.world.uow_factory() as uow:
        return uow.generations.get(generation_id)


# --- the version, the files and the total (PAR-02, PAR-04) --------------------------------------


def test_the_run_stores_version_1_ready_with_a_docx_and_a_pdf(gen):
    _, parecer = a_ready_parecer(gen)

    assert (parecer.kind, parecer.state, parecer.version_number) == (
        DocumentKind.PARECER,
        GenerationState.PRONTO,
        1,
    )
    assert sorted(f.format for f in parecer.files) == [DocumentFormat.DOCX, DocumentFormat.PDF]
    for fmt in DocumentFormat:
        assert zipfile.is_zipfile(file_path(gen, parecer, fmt)) == (fmt is DocumentFormat.DOCX)


def test_the_total_of_the_snapshot_is_the_one_of_the_table_and_no_file_prints_it(gen):
    add_scenario_211(gen.world)
    table = ready(gen, DocumentKind.TABELA)
    board(gen)

    parecer = ready(gen, DocumentKind.PARECER)

    assert parecer.snapshot["total"] == table.snapshot["total"]
    assert parecer.snapshot["subtotals"] == table.snapshot["subtotals"]
    for fmt, text in flat_texts(gen, parecer).items():
        for forbidden in ("Total geral", "Mínimo de referência", "Observações"):
            assert forbidden not in text, (fmt, forbidden)
        assert table.snapshot["total"].replace(".", ",") not in text, fmt  # "211,00"


def test_the_paragraph_of_the_model_and_the_titular_member_lines_are_in_both_files(gen):
    _, parecer = a_ready_parecer(gen)

    for fmt, text in flat_texts(gen, parecer).items():
        assert (
            "Aos dois dias do mês de abril de dois mil e vinte e cinco, reuniram-se os membros "
            "da Banca de Análise, nomeados pela Portaria nº 77/2025, Ana Presidente Souza "
            "(presidente), Bruno Membro Lima, responsáveis por analisar o Relatório de "
            "Atividades do Professor" in text
        ), fmt
        assert "referente ao interstício de 23/11/2022 a 23/11/2024, para Classe D" in text, fmt
        assert "Após a análise, os membros APROVARAM o referido relatório." in text, fmt
        assert "Belém, 2 de Abril de 2025." in text, fmt
        assert text.endswith("PRESIDENTE: Ana Presidente Souza MEMBRO 1: Bruno Membro Lima"), fmt
        assert "Carla Suplente Reis" not in text, fmt


def test_the_unfavorable_conclusion_says_nao_aprovaram(gen):
    ready_table(gen)
    board(gen, OpinionConclusion.DESFAVORAVEL)

    parecer = ready(gen, DocumentKind.PARECER)

    assert parecer.snapshot["conclusion"] == "DESFAVORAVEL"
    for fmt, text in flat_texts(gen, parecer).items():
        assert "os membros NÃO APROVARAM o referido relatório." in text, fmt
        assert "os membros APROVARAM" not in text, fmt


# --- the header with the campus of the unit (PMOD-02, PMOD-03) ----------------------------------


def test_the_campus_of_the_unit_is_a_line_of_the_header_in_both_files(gen):
    _, parecer = a_ready_parecer(gen)

    for fmt, text in flat_texts(gen, parecer).items():
        assert text.startswith(
            "Universidade Federal do Pará Campus Universitário do Tocantins/Cametá "
            "Faculdade de Sistemas de Informação – FASI PARECER"
        ), fmt


def test_a_unit_without_a_parent_campus_has_a_header_of_two_lines(gen):
    ready_table(gen)
    board(gen)
    with gen.world.uow_factory() as uow:
        unit = uow.units.get(gen.world.process.unit_id)
        assert unit.parent_id is not None  # the premise: the seed links the unit to the campus
        uow.units.update(dataclasses.replace(unit, parent_id=None))
        uow.commit()

    parecer = ready(gen, DocumentKind.PARECER)

    for fmt, text in flat_texts(gen, parecer).items():
        assert text.startswith(
            "Universidade Federal do Pará Faculdade de Sistemas de Informação – FASI PARECER"
        ), fmt
        assert "Campus Universitário" not in text, fmt


# --- the snapshot -------------------------------------------------------------------------------


def test_the_snapshot_names_the_table_the_versions_used_the_fields_and_the_ordinance(gen):
    table = ready_table(gen)
    ready(gen, DocumentKind.RELATORIO)
    board(gen)

    parecer = ready(gen, DocumentKind.PARECER)

    snapshot = parecer.snapshot
    assert snapshot["table_generation_id"] == str(table.id)
    assert snapshot["table_version"] == table.snapshot["table_version"]
    assert snapshot["interstice"] == {"start": "2022-11-23", "end": "2024-11-23"}
    assert snapshot["versions_used"] == {"TABELA": 1, "RELATORIO": 1, "COMPROVANTE": None}
    assert snapshot["conclusion"] == "FAVORAVEL"
    assert (snapshot["opinion_date"], snapshot["place"]) == ("2025-04-02", "Belém")
    assert (snapshot["ordinance_number"], snapshot["ordinance_date"]) == ("77/2025", "2025-03-10")
    assert snapshot["members"] == [{"name": m.name, "role": m.role.value} for m in MEMBERS]
    assert set(snapshot) == {
        "table_generation_id",
        "table_version",
        "interstice",
        "total",
        "subtotals",
        "minimum",
        "versions_used",
        "conclusion",
        "opinion_date",
        "place",
        "ordinance_number",
        "ordinance_date",
        "members",
    }
    for text in flat_texts(gen, parecer).values():
        assert "Relatório de Atividades: versão" not in text
        assert "Comprovante de Documentos" not in text


def test_the_snapshot_keeps_the_minimum_of_the_table(gen):
    table = ready_table(gen)
    board(gen)

    parecer = ready(gen, DocumentKind.PARECER)

    assert table.snapshot["minimum"] == {"status": "NAO_ATINGE", "value": "100.00"}
    assert parecer.snapshot["minimum"] == table.snapshot["minimum"]


def test_the_minimum_saved_in_the_table_wins_over_the_one_of_now(gen):
    table = ready_table(gen)
    craft_ready_table(
        gen.world,
        gen.clock,
        {**table.snapshot, "minimum": {"status": "NAO_DEFINIDO", "value": None}},
    )
    board(gen)

    parecer = ready(gen, DocumentKind.PARECER)

    assert parecer.snapshot["minimum"] == {"status": "NAO_DEFINIDO", "value": None}


def test_a_table_of_before_the_field_uses_the_minimum_calculated_now(gen):
    table = ready_table(gen)
    old = {k: v for k, v in table.snapshot.items() if k != "minimum"}
    craft_ready_table(gen.world, gen.clock, old)
    board(gen)

    parecer = ready(gen, DocumentKind.PARECER)

    assert parecer.snapshot["minimum"] == {"status": "NAO_ATINGE", "value": "100.00"}


# --- the score moves between the request and the run (PAR-10) -----------------------------------


def test_a_validated_activity_changed_between_the_request_and_the_run_fails_the_row(gen):
    ready_table(gen)
    board(gen)
    before = stored_files(gen)
    requested = ask(gen, DocumentKind.PARECER)
    add_activity(gen.world, title="Outra orientação depois do pedido")

    run_one(gen)

    failed = run_row(gen, requested.id)
    assert failed.state is GenerationState.FALHOU
    assert failed.error_code is GenerationCode.TABELA_DESATUALIZADA
    assert failed.error_message == OUTDATED_MESSAGE
    assert failed.version_number is None and failed.files == ()
    assert stored_files(gen) == before
    # no number was spent: after a new Tabela the Parecer is version 1
    ready(gen, DocumentKind.TABELA)
    assert ready(gen, DocumentKind.PARECER).version_number == 1


def test_a_conclusion_cleared_between_the_request_and_the_run_fails_the_row_with_its_code(gen):
    ready_table(gen)
    board(gen)
    requested = ask(gen, DocumentKind.PARECER)
    with gen.world.uow_factory() as uow:
        saved = uow.opinions.get(gen.world.process.id)
        uow.opinions.update(
            BoardOpinion(saved.process_id, None, saved.opinion_date, saved.place),
            gen.world.admin.id,
            saved.version,
        )
        uow.commit()

    run_one(gen)

    failed = run_row(gen, requested.id)
    assert failed.state is GenerationState.FALHOU
    assert failed.error_code is GenerationCode.CONCLUSAO_AUSENTE
    assert failed.files == ()


# --- again, history (PAR-14) --------------------------------------------------------------------


def test_asking_again_makes_version_2_and_both_stay_in_the_history_and_on_disk(gen):
    _, first = a_ready_parecer(gen)
    before = {fmt: file_path(gen, first, fmt).read_bytes() for fmt in DocumentFormat}

    second = ready(gen, DocumentKind.PARECER)

    assert (first.version_number, second.version_number) == (1, 2)
    with gen.world.uow_factory() as uow:
        history = uow.generations.list_for_process(gen.world.process.id, DocumentKind.PARECER)
    assert sorted(g.version_number for g in history if g.state is GenerationState.PRONTO) == [1, 2]
    for version in (first, second):
        for fmt in DocumentFormat:
            assert file_path(gen, version, fmt).is_file()
    assert {f.internal_name for f in first.files}.isdisjoint(f.internal_name for f in second.files)
    assert {fmt: file_path(gen, first, fmt).read_bytes() for fmt in DocumentFormat} == before


# --- no AI (PAR-11) -----------------------------------------------------------------------------


def test_the_parecer_is_made_without_calling_the_ai(gen, no_ai):
    _, parecer = a_ready_parecer(gen)

    assert parecer.state is GenerationState.PRONTO
    assert no_ai == []


# --- restart (AD-012) ---------------------------------------------------------------------------


def test_a_parecer_left_generating_by_a_restart_is_closed_as_interrupted(gen):
    ready_table(gen)
    board(gen)
    requested = ask(gen, DocumentKind.PARECER)
    with gen.world.uow_factory() as uow:
        assert uow.generations.claim_next(gen.clock.now()).id == requested.id
        uow.commit()
    gen.clock.advance(minutes=5)

    RecoverInterruptedGenerations(
        gen.world.uow_factory, gen.world.audit, gen.clock, gen.generated
    ).execute()

    row = run_row(gen, requested.id)
    assert row.state is GenerationState.FALHOU
    assert row.error_code is GenerationCode.INTERROMPIDA
