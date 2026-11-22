"""PAR-02 to PAR-04, PAR-10, PAR-11, PAR-14, VER-08: running the generation of the Parecer."""

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


def comma(amount: str) -> str:
    return amount.replace(".", ",")


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


def test_the_total_geral_of_the_snapshot_and_of_both_files_is_the_one_of_the_table(gen):
    add_scenario_211(gen.world)
    table = ready(gen, DocumentKind.TABELA)
    board(gen)

    parecer = ready(gen, DocumentKind.PARECER)

    total = table.snapshot["total"]
    assert parecer.snapshot["total"] == total
    assert parecer.snapshot["subtotals"] == table.snapshot["subtotals"]
    for fmt, text in texts(gen, parecer).items():
        assert f"Total geral\n{comma(total)}" in text, fmt


def test_the_conclusion_sentence_and_the_three_signature_lines_are_in_both_files(gen):
    _, parecer = a_ready_parecer(gen)

    for fmt, text in texts(gen, parecer).items():
        assert "A banca manifesta-se FAVORÁVEL à" in text.replace("\n", " "), fmt
        assert "referente ao interstício de 23/11/2022 a 23/11/2024." in text.replace("\n", " ")
        for member in MEMBERS:
            assert member.name in text, (fmt, member.name)
        assert text.count("_" * 42) == 3, fmt


def test_the_unfavorable_conclusion_says_desfavoravel(gen):
    ready_table(gen)
    board(gen, OpinionConclusion.DESFAVORAVEL)

    parecer = ready(gen, DocumentKind.PARECER)

    assert parecer.snapshot["conclusion"] == "DESFAVORAVEL"
    for text in texts(gen, parecer).values():
        assert "DESFAVORÁVEL" in text and "FAVORÁVEL à" not in text.replace("DESFAVORÁVEL", "")


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
    for text in texts(gen, parecer).values():
        assert "Relatório de Atividades: versão 1" in text.replace("\n", " ")
        assert "Comprovante de Documentos: não gerado" in text.replace("\n", " ")


def test_the_snapshot_keeps_the_minimum_of_the_table(gen):
    table = ready_table(gen)
    board(gen)

    parecer = ready(gen, DocumentKind.PARECER)

    assert table.snapshot["minimum"] == {"status": "NAO_ATINGE", "value": "100.00"}
    assert parecer.snapshot["minimum"] == table.snapshot["minimum"]
    for text in texts(gen, parecer).values():
        assert "Mínimo de referência: 100,00 pontos" in text


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
    for text in texts(gen, parecer).values():
        assert "Mínimo de referência: não definido pela norma aplicável" in text


def test_a_table_of_before_the_field_uses_the_minimum_calculated_now(gen):
    table = ready_table(gen)
    old = {k: v for k, v in table.snapshot.items() if k != "minimum"}
    craft_ready_table(gen.world, gen.clock, old)
    board(gen)

    parecer = ready(gen, DocumentKind.PARECER)

    assert parecer.snapshot["minimum"] == {"status": "NAO_ATINGE", "value": "100.00"}
    for text in texts(gen, parecer).values():
        assert "Mínimo de referência: 100,00 pontos" in text


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
            BoardOpinion(saved.process_id, None, saved.opinion_date, saved.place, saved.notes),
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

    second = ready(gen, DocumentKind.PARECER)

    assert (first.version_number, second.version_number) == (1, 2)
    with gen.world.uow_factory() as uow:
        history = uow.generations.list_for_process(gen.world.process.id, DocumentKind.PARECER)
    assert sorted(g.version_number for g in history if g.state is GenerationState.PRONTO) == [1, 2]
    for version in (first, second):
        for fmt in DocumentFormat:
            assert file_path(gen, version, fmt).is_file()
    assert {f.internal_name for f in first.files}.isdisjoint(f.internal_name for f in second.files)


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
