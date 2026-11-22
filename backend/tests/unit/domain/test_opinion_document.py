"""PAR-03 to PAR-06, PAR-11, PAR-12: the text of the Parecer built from the Tabela snapshot."""

import inspect
from datetime import date
from decimal import Decimal

import pytest

from app.domain.entities.board import OpinionConclusion
from app.domain.entities.career import Modality
from app.domain.entities.generated import DocumentKind
from app.domain.rules import opinion_document
from app.domain.rules.opinion_document import build_opinion
from app.domain.rules.scoring_verification import MinimumComparison, MinimumStatus
from tests.unit.domain.board_document_support import (
    PAGE,
    PROFESSOR,
    UNIT,
    member,
    opinion,
    ordinance,
    process,
)

GROUP_NAMES = {
    1: "Atividades de ensino",
    2: "Orientações",
    3: "Bancas",
    4: "Extensão",
    5: "Pesquisa",
    6: "Administração",
    7: "Capacitação",
    8: "Outras atividades",
}
# The subtotals do not add up to the total on purpose: the Parecer copies, never sums (PAR-04).
SNAPSHOT = {
    "total": "211.00",
    "subtotals": {"1": "100.00", "2": "50.50", "3": "0.00", "4": "7.00", "5": "30.00"},
    "table_version": {"id": "x", "name": "Tabela sintética", "norm_reference": "n"},
}
VERSIONS = {DocumentKind.TABELA: 3, DocumentKind.RELATORIO: 2, DocumentKind.COMPROVANTE: None}
MINIMUM = MinimumComparison(MinimumStatus.ATINGE, Decimal("200.00"), Decimal("211.00"))
UNDEFINED = MinimumComparison(MinimumStatus.NAO_DEFINIDO, None, Decimal("211.00"))


def build(
    *,
    proc=None,
    ordinance_=None,
    opinion_=None,
    snapshot=SNAPSHOT,
    versions=VERSIONS,
    minimum=MINIMUM,
):
    return build_opinion(
        proc or process(),
        PROFESSOR,
        UNIT,
        ordinance_ or ordinance(),
        opinion_ or opinion(),
        snapshot,
        versions,
        minimum,
        GROUP_NAMES,
        PAGE,
    )


def section(document, key):
    return next(s for s in document.sections if s.key == key)


def all_text(document) -> str:
    lines = list(document.header_lines) + [document.title]
    for s in document.sections:
        lines += [s.heading or "", *s.lines]
        lines += [f"{r.label} {r.value}" for r in s.rows]
        if s.total is not None:
            lines.append(f"{s.total.label} {s.total.value}")
    lines += [f"{sig.name} {sig.role}" for sig in document.signatures]
    return "\n".join(lines)


# --- order and header (PAR-03) --------------------------------------------------------------


def test_the_sections_come_in_the_order_of_par_03():
    document = build()

    assert [s.key for s in document.sections] == [
        "identificacao",
        "portaria",
        "intersticio",
        "documentos",
        "pontos",
        "minimo",
        "conclusao",
        "observacoes",
        "local_data",
    ]


def test_the_header_names_the_university_and_the_unit_and_the_title_is_parecer():
    document = build()

    assert "Universidade Federal do Pará" in document.header_lines
    assert document.header_lines[-1] == UNIT.name
    assert document.title == "PARECER"


def test_the_page_is_the_one_given_so_it_looks_like_the_relatorio():
    assert build().page is PAGE


def test_the_ordinance_section_has_the_number_and_the_date():
    lines = section(build(), "portaria").lines

    assert any("123/2025" in line and "10/03/2025" in line for line in lines)


def test_an_ordinance_without_number_or_date_leaves_the_blanks():
    document = build(ordinance_=ordinance(number=None, when=None))

    line = " ".join(section(document, "portaria").lines)
    assert "__________" in line
    assert "___/___/___" in line


def test_the_interstice_section_has_the_period_of_the_process():
    assert any("23/11/2022 a 23/11/2024" in line for line in section(build(), "intersticio").lines)


# --- identification as typed (NMOV-01) ------------------------------------------------------


def test_the_identification_has_the_six_fields_exactly_as_the_process_has_them():
    text = "\n".join(section(build(), "identificacao").lines)

    for expected in (
        "Maria Docente da Silva",
        "1234567",
        UNIT.name,
        "Promoção",
        "nível 4",
        "classe B",
        "Adjunto",
        "nível 1",
        "classe C",
        "Associado",
    ):
        assert expected in text


def test_a_progression_says_progressao_in_the_identification():
    text = "\n".join(section(build(proc=process(Modality.PROGRESSAO)), "identificacao").lines)

    assert "Progressão" in text
    assert "Promoção" not in text


def test_denominations_out_of_the_usual_pattern_are_copied_as_typed():
    proc = process(current_denomination="Titular-Livre", target_denomination="Denominação Nova")

    text = "\n".join(section(build(proc=proc), "identificacao").lines)

    assert "Titular-Livre" in text
    assert "Denominação Nova" in text


# --- documents analyzed ---------------------------------------------------------------------


def test_the_analyzed_documents_name_the_version_used_of_each_one():
    lines = section(build(), "documentos").lines

    assert any("Tabela" in line and "versão 3" in line for line in lines)
    assert any("Relatório" in line and "versão 2" in line for line in lines)


def test_a_document_never_generated_reads_nao_gerado():
    lines = section(build(), "documentos").lines

    assert any("Comprovante" in line and "não gerado" in line for line in lines)


# --- points copied from the snapshot (PAR-04) -----------------------------------------------


def test_the_points_are_the_snapshot_ones_formatted_in_portuguese_for_groups_i_to_viii():
    rows = section(build(), "pontos").rows

    assert [(r.label, r.value) for r in rows] == [
        ("I - Atividades de ensino", "100,00"),
        ("II - Orientações", "50,50"),
        ("III - Bancas", "0,00"),
        ("IV - Extensão", "7,00"),
        ("V - Pesquisa", "30,00"),
        ("VI - Administração", "0,00"),
        ("VII - Capacitação", "0,00"),
        ("VIII - Outras atividades", "0,00"),
    ]


def test_the_total_is_the_snapshot_total_even_when_the_subtotals_do_not_add_up():
    total = section(build(), "pontos").total

    assert (total.label, total.value) == ("Total geral", "211,00")


# --- minimum (PAR-06) -----------------------------------------------------------------------


def test_an_undefined_minimum_is_written_without_a_number():
    lines = section(build(minimum=UNDEFINED), "minimo").lines

    assert lines == ("Mínimo de referência: não definido pela norma aplicável",)


def test_a_numeric_minimum_is_written_with_its_value():
    lines = section(build(), "minimo").lines

    assert lines == ("Mínimo de referência: 200,00 pontos",)


# --- conclusion (PAR-05, PAR-12) ------------------------------------------------------------


def test_a_favorable_promotion_reads_the_sentence_of_the_spec():
    lines = section(build(), "conclusao").lines

    assert lines == (
        "A banca manifesta-se FAVORÁVEL à promoção de Maria Docente da Silva, do nível 4 da "
        "classe B (Adjunto) para o nível 1 da classe C (Associado), referente ao interstício "
        "de 23/11/2022 a 23/11/2024.",
    )


def test_an_unfavorable_progression_reads_the_same_sentence_with_desfavoravel():
    document = build(
        proc=process(Modality.PROGRESSAO),
        opinion_=opinion(OpinionConclusion.DESFAVORAVEL),
    )

    assert section(document, "conclusao").lines == (
        "A banca manifesta-se DESFAVORÁVEL à progressão de Maria Docente da Silva, do nível 4 "
        "da classe B (Adjunto) para o nível 1 da classe C (Associado), referente ao interstício "
        "de 23/11/2022 a 23/11/2024.",
    )


def test_without_a_conclusion_the_document_is_never_written():
    with pytest.raises(ValueError):
        build(opinion_=opinion(conclusion=None))


# --- notes, place and date ------------------------------------------------------------------


def test_the_notes_are_a_section_of_their_own():
    document = build(opinion_=opinion(notes="A banca registra elogios ao relatório."))

    assert section(document, "observacoes").lines == ("A banca registra elogios ao relatório.",)


@pytest.mark.parametrize("notes", [None, "", "   \n "])
def test_empty_notes_do_not_create_a_section(notes):
    document = build(opinion_=opinion(notes=notes))

    assert "observacoes" not in [s.key for s in document.sections]


def test_place_and_date_are_written_with_the_blanks_when_empty():
    filled = build(opinion_=opinion(place="Belém", opinion_date=date(2025, 4, 2)))
    empty = build(opinion_=opinion(place=None, opinion_date=None))

    assert section(filled, "local_data").lines == ("Belém, 02/04/2025",)
    assert section(empty, "local_data").lines == ("__________, ___/___/___",)


# --- signatures -----------------------------------------------------------------------------


def test_each_member_gets_a_signature_line_in_the_order_of_the_ordinance():
    document = build()

    assert [(s.name, s.role) for s in document.signatures] == [
        ("Ana Presidente Souza", "Presidente"),
        ("Bruno Membro Lima", "Membro"),
        ("Carla Suplente Reis", "Suplente"),
    ]


def test_the_signatures_come_after_the_conclusion_and_the_place_and_date():
    text = all_text(build())

    assert text.index("A banca manifesta-se") < text.index("Belém, 02/04/2025")
    assert text.index("Belém, 02/04/2025") < text.index("Ana Presidente Souza Presidente")


def test_one_member_gives_one_signature():
    document = build(ordinance_=ordinance(members=[member("Só Um Membro")]))

    assert [s.name for s in document.signatures] == ["Só Um Membro"]


# --- no clock, no AI (PAR-11) ---------------------------------------------------------------


def test_the_same_input_gives_the_same_document():
    assert build() == build()


def test_the_module_reads_no_clock_and_calls_no_ai():
    source = inspect.getsource(opinion_document)

    for forbidden in ("now(", "today(", "utcnow(", "maritalk", "import time", "app.infrastructure"):
        assert forbidden not in source.lower()
