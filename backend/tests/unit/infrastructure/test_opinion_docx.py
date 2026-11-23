"""PMOD-01, PMOD-02, PMOD-04 to PMOD-07, PMOD-13, PMOD-19, PMOD-20: the Parecer written as DOCX
with python-docx, after the official model."""

import zipfile
from dataclasses import replace

import pytest
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.table import Table
from docx.text.paragraph import Paragraph
from lxml import etree

from app.domain.entities.board import BoardRole, OpinionConclusion
from app.infrastructure.documents.opinion_docx import write_opinion_docx
from tests.unit.domain.board_document_support import MEMBERS, member
from tests.unit.infrastructure.board_writer_support import opinion_model

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}
PARAGRAPH = (
    "Aos dois dias do mês de abril de dois mil e vinte e cinco, reuniram-se os membros da "
    "Banca de Análise, nomeados pela Portaria nº 123/2025, Ana Presidente Souza (presidente), "
    "Bruno Membro Lima, responsáveis por analisar o Relatório de Atividades do Professor "
    "Adjunto Nível IV Maria Docente da Silva, para fins de progressão funcional do docente, "
    "referente ao interstício "
    "de 23/11/2022 a 23/11/2024, para Classe C (Associado) Nível I. Após a análise, os membros "
    "APROVARAM o referido relatório."
)
THREE_TITULARS = (*MEMBERS[:2], member("Carla Membro Reis"))


def write(tmp_path, model):
    target = tmp_path / ".tmp-0123456789abcdef"  # the storage hands out a path with no extension
    write_opinion_docx(model, target)
    return target


def body_texts(path) -> list[str]:
    """Every text of the body in document order: paragraphs, and the cells of a table row by row."""
    document = Document(str(path))
    texts = []
    for child in document.element.body.iterchildren():
        if child.tag == f"{{{W}}}p":
            texts.append(Paragraph(child, document).text)
        elif child.tag == f"{{{W}}}tbl":
            for row in Table(child, document).rows:
                texts.extend(cell.text for cell in row.cells)
    return texts


def paragraphs(path) -> list[Paragraph]:
    return Document(str(path)).paragraphs


def the_paragraph(path) -> Paragraph:
    return next(p for p in paragraphs(path) if p.text.startswith("Aos "))


def test_the_file_is_written_at_the_given_path_and_opens_as_a_docx(tmp_path):
    target = write(tmp_path, opinion_model())

    assert zipfile.is_zipfile(target)
    assert Document(str(target)).paragraphs


def test_the_body_has_only_the_elements_of_the_model_in_order(tmp_path):
    texts = body_texts(write(tmp_path, opinion_model()))

    assert texts == [
        "Universidade Federal do Pará",
        "Campus Universitário Sintético",
        "Faculdade de Testes Sintéticos – FATS",
        "PARECER",
        "Belém, 2 de Abril de 2025.",
        PARAGRAPH,
        "PRESIDENTE: Ana Presidente Souza",
        "MEMBRO 1: Bruno Membro Lima",
    ]


def test_without_a_campus_the_header_has_two_lines(tmp_path):
    texts = body_texts(write(tmp_path, opinion_model(parent_unit=None)))

    assert texts[:3] == [
        "Universidade Federal do Pará",
        "Faculdade de Testes Sintéticos – FATS",
        "PARECER",
    ]


def test_the_page_is_a4_portrait_with_the_margins_of_the_model(tmp_path):
    document = Document(str(write(tmp_path, opinion_model())))

    section = document.sections[0]
    assert (round(section.page_width.mm), round(section.page_height.mm)) == (210, 297)
    assert round(section.left_margin.mm, 2) == 30.0
    assert round(section.right_margin.mm, 2) == 20.0
    assert round(section.top_margin.mm, 2) == 30.0
    assert round(section.bottom_margin.mm, 2) == 20.0


def test_the_body_and_the_header_use_the_font_of_the_page_at_twelve_points(tmp_path):
    small = replace(opinion_model().page, font_name="Times New Roman", font_size_pt=9)
    document = Document(str(write(tmp_path, replace(opinion_model(), page=small))))

    normal = document.styles["Normal"].font
    assert (normal.name, normal.size.pt) == ("Times New Roman", 12)
    header, body = document.paragraphs[0], document.paragraphs[5]
    for paragraph in (header, body):
        assert all(run.font.name is None and run.font.size is None for run in paragraph.runs)


def test_the_header_is_centered_and_only_its_last_line_has_the_horizontal_rule(tmp_path):
    document = Document(str(write(tmp_path, opinion_model())))

    header = document.paragraphs[:3]
    assert all(p.alignment == WD_ALIGN_PARAGRAPH.CENTER for p in header)
    borders = [p._p.findall("w:pPr/w:pBdr/w:bottom", NS) for p in document.paragraphs]
    assert [len(b) > 0 for b in borders[:6]] == [False, False, True, False, False, False]
    assert borders[2][0].get(f"{{{W}}}val") == "single"


def test_the_title_is_arial_bold_and_centered(tmp_path):
    title = Document(str(write(tmp_path, opinion_model()))).paragraphs[3]

    assert title.text == "PARECER"
    assert title.alignment == WD_ALIGN_PARAGRAPH.CENTER
    assert [(r.font.name, r.bold) for r in title.runs] == [("Arial", True)]


def test_the_place_and_date_line_is_arial_and_starts_at_half_the_text_width(tmp_path):
    line = Document(str(write(tmp_path, opinion_model()))).paragraphs[4]

    assert line.text == "Belém, 2 de Abril de 2025."
    assert all(run.font.name == "Arial" for run in line.runs)
    # half of the text width: (210 - 30 - 20) / 2, to the twip the file stores
    assert line.paragraph_format.left_indent.mm == pytest.approx(80.0, abs=0.05)
    assert line.alignment in (None, WD_ALIGN_PARAGRAPH.LEFT)


def test_the_paragraph_is_justified_with_a_first_line_indent_and_one_and_a_half_spacing(tmp_path):
    paragraph = the_paragraph(write(tmp_path, opinion_model()))

    assert paragraph.alignment == WD_ALIGN_PARAGRAPH.JUSTIFY
    assert round(paragraph.paragraph_format.first_line_indent.cm, 2) == 1.25
    assert paragraph.paragraph_format.line_spacing == 1.5


def test_only_the_date_words_and_the_current_situation_with_the_name_are_bold(tmp_path):
    paragraph = the_paragraph(write(tmp_path, opinion_model()))

    assert [r.text for r in paragraph.runs if r.bold] == [
        "dois dias do mês de abril de dois mil e vinte e cinco",
        "Adjunto Nível IV Maria Docente da Silva",
    ]
    assert next(r for r in paragraph.runs if r.text == "Aos ").bold is not True
    assert not any(r.bold for r in paragraph.runs if r.text.endswith("do Professor "))


def test_a_favorable_and_an_unfavorable_conclusion_end_the_paragraph_differently(tmp_path):
    model = opinion_model(conclusion=OpinionConclusion.DESFAVORAVEL)

    paragraph = the_paragraph(write(tmp_path, model))

    assert paragraph.text.endswith("os membros NÃO APROVARAM o referido relatório.")


def test_the_member_lines_are_centered_with_no_signature_rule_and_no_alternate(tmp_path):
    path = write(tmp_path, opinion_model())
    texts = body_texts(path)

    lines = [p for p in paragraphs(path) if p.text.startswith(("PRESIDENTE:", "MEMBRO"))]
    assert [p.text for p in lines] == texts[-2:]
    assert all(p.alignment == WD_ALIGN_PARAGRAPH.CENTER for p in lines)
    assert not any("___" in t for t in texts)
    assert not any(r.underline for p in lines for r in p.runs)
    assert "Carla Suplente Reis" not in " ".join(texts)


def test_a_third_titular_member_is_one_more_line(tmp_path):
    texts = body_texts(write(tmp_path, opinion_model(members=THREE_TITULARS)))

    assert texts[-3:] == [
        "PRESIDENTE: Ana Presidente Souza",
        "MEMBRO 1: Bruno Membro Lima",
        "MEMBRO 2: Carla Membro Reis",
    ]


def test_there_is_no_table_and_no_page_footer(tmp_path):
    path = write(tmp_path, opinion_model())

    assert Document(str(path)).tables == []
    package = zipfile.ZipFile(path)
    for name in (n for n in package.namelist() if n.startswith("word/footer")):
        footer = etree.fromstring(package.read(name))
        assert footer.findall(".//w:instrText", NS) == []
        assert "".join(footer.itertext()).strip() == ""


def test_control_characters_in_a_name_do_not_break_the_file(tmp_path):
    members = (member("Ana\x00 Souza\x0b", BoardRole.PRESIDENTE),)

    texts = body_texts(write(tmp_path, opinion_model(members=members)))

    assert "PRESIDENTE: Ana Souza" in texts
    assert "Ana Souza (presidente), responsáveis por analisar" in texts[5]


def test_the_document_title_property_is_parecer(tmp_path):
    document = Document(str(write(tmp_path, opinion_model())))

    assert document.core_properties.title == "PARECER"
