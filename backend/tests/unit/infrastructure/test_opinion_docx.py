"""PAR-03: the Parecer written as DOCX with python-docx, in the order of the spec."""

import zipfile

from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph
from lxml import etree

from app.domain.entities.board import BoardRole
from app.infrastructure.documents.opinion_docx import write_opinion_docx
from tests.unit.domain.board_document_support import MEMBERS, member
from tests.unit.infrastructure.board_writer_support import opinion_model

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}


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


def test_the_file_is_written_at_the_given_path_and_opens_as_a_docx(tmp_path):
    target = write(tmp_path, opinion_model())

    assert zipfile.is_zipfile(target)
    assert Document(str(target)).paragraphs


def test_the_text_comes_in_the_order_of_par_03(tmp_path):
    texts = body_texts(write(tmp_path, opinion_model()))

    markers = [
        "Universidade Federal do Pará",
        "Faculdade de Testes Sintéticos",
        "PARECER",
        "Identificação",
        "Docente: Maria Docente da Silva",
        "Portaria da banca",
        "Portaria da banca: nº 123/2025, de 10/03/2025.",
        "Interstício",
        "Documentos analisados",
        "Tabela de Pontuação: versão 3",
        "Pontuação por grupo",
        "I - Atividades de ensino",
        "Total geral",
        "Mínimo de referência: 200,00 pontos",
        "Conclusão",
        "A banca manifesta-se FAVORÁVEL",
        "Observações",
        "Sem observações adicionais.",
        "Belém, 02/04/2025",
        "Ana Presidente Souza",
    ]
    positions = []
    for marker in markers:
        matches = [i for i, t in enumerate(texts) if t == marker or t.startswith(marker + " ")]
        assert matches, marker
        positions.append(matches[0])
    assert positions == sorted(positions)
    assert len(set(positions)) == len(positions)


def test_the_header_is_centered_and_the_title_is_parecer(tmp_path):
    document = Document(str(write(tmp_path, opinion_model())))

    first = document.paragraphs[:4]
    assert [p.text for p in first] == [
        "Serviço Público Federal",
        "Universidade Federal do Pará",
        "Faculdade de Testes Sintéticos",
        "PARECER",
    ]
    assert all(p.alignment == 1 for p in first)  # WD_ALIGN_PARAGRAPH.CENTER


def test_the_total_geral_of_the_document_is_the_one_of_the_model(tmp_path):
    model = opinion_model()
    document = Document(str(write(tmp_path, model)))

    rows = [[c.text for c in row.cells] for row in document.tables[0].rows]
    assert rows[-1] == ["Total geral", "211,00"]
    assert rows[0] == ["I - Atividades de ensino", "100,00"]
    assert len(rows) == 9  # the eight groups and the total


def test_three_members_give_three_signature_lines_with_name_and_role(tmp_path):
    texts = body_texts(write(tmp_path, opinion_model()))

    tail = texts[texts.index("Ana Presidente Souza") - 1 :]
    assert tail == [
        "_" * 42, "Ana Presidente Souza", "Presidente",
        "_" * 42, "Bruno Membro Lima", "Membro",
        "_" * 42, "Carla Suplente Reis", "Suplente",
    ]  # fmt: skip


def test_one_more_member_is_one_more_signature_line(tmp_path):
    members = (*MEMBERS, member("Diego Membro Costa", BoardRole.MEMBRO))

    texts = body_texts(write(tmp_path, opinion_model(members=members)))

    assert texts.count("_" * 42) == 4
    assert texts[-2:] == ["Diego Membro Costa", "Membro"]


def test_control_characters_in_a_name_or_in_the_notes_do_not_break_the_file(tmp_path):
    members = (member("Ana\x00 Souza\x0b", BoardRole.PRESIDENTE),)
    model = opinion_model(members=members, notes="Linha um\x00\x0b\nLinha dois ü")

    texts = body_texts(write(tmp_path, model))

    assert "Ana Souza" in texts
    assert "Linha um" in texts
    assert "Linha dois ü" in texts


def test_the_page_is_a4_with_the_margins_and_the_font_of_the_model(tmp_path):
    document = Document(str(write(tmp_path, opinion_model())))

    section = document.sections[0]
    assert (round(section.page_width.mm), round(section.page_height.mm)) == (210, 297)
    assert round(section.left_margin.mm, 2) == 30.0
    assert round(section.right_margin.mm, 2) == 20.0
    assert round(section.top_margin.mm, 2) == 30.0
    assert round(section.bottom_margin.mm, 2) == 20.0
    normal = document.styles["Normal"].font
    assert (normal.name, normal.size.pt) == ("Liberation Serif", 12)


def test_the_footer_has_the_page_and_numpages_fields(tmp_path):
    path = write(tmp_path, opinion_model())

    footers = [n for n in zipfile.ZipFile(path).namelist() if n.startswith("word/footer")]
    footer = etree.fromstring(zipfile.ZipFile(path).read(footers[0]))
    assert [t.text.strip() for t in footer.findall(".//w:instrText", NS)] == ["PAGE", "NUMPAGES"]


def test_without_notes_there_is_no_observations_section(tmp_path):
    texts = body_texts(write(tmp_path, opinion_model(notes=None)))

    assert "Observações" not in texts
