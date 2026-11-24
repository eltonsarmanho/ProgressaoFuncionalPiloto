"""REQ-02, REQ-03, REQ-05, REQ-07: the Requerimento written as DOCX with python-docx, in the order
of the public PROGEP model."""

import zipfile
from dataclasses import replace
from datetime import date

import pytest
from docx import Document
from lxml import etree

from app.infrastructure.documents import emblem
from app.infrastructure.documents.emblem import EmblemUnavailable
from app.infrastructure.documents.request_docx import write_request_docx
from tests.unit.domain.board_document_support import PROFESSOR
from tests.unit.infrastructure.board_writer_support import request_model

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W, "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"}

PARAGRAPH = (
    "Eu, Maria Docente da Silva, Matrícula SIAPE 1234567, docente do (X) Magistério "
    "Superior/ (  ) Ensino Básico e Tecnológico, atualmente lotado no (a) "
    "Faculdade de Testes Sintéticos, solicito promoção funcional, do nível 4 da classe B "
    "(Adjunto) para o nível 1 da classe C (Associado), referente ao interstício "
    "23/11/2022 a 23/11/2024."
)


def write(tmp_path, model):
    target = tmp_path / ".tmp-0123456789abcdef"  # the storage hands out a path with no extension
    write_request_docx(model, target)
    return target


def texts(path) -> list[str]:
    return [p.text for p in Document(str(path)).paragraphs if p.text.strip()]


def test_the_file_is_written_at_the_given_path_and_opens_as_a_docx(tmp_path):
    target = write(tmp_path, request_model())

    assert zipfile.is_zipfile(target)
    assert texts(target)


def test_the_paragraphs_come_in_the_order_of_the_model(tmp_path):
    found = texts(write(tmp_path, request_model(last_opinion=date(2025, 4, 2))))

    assert found == [
        "MINISTÉRIO DA EDUCAÇÃO",
        "UNIVERSIDADE FEDERAL DO PARÁ",
        "PRÓ-REITORIA DE DESENVOLVIMENTO E GESTÃO DE PESSOAL",
        "REQUERIMENTO DE PROGRESSÃO/PROMOÇÃO/REVISÃO - DOCENTES (MAGISTÉRIO SUPERIOR E EBTT)",
        "Prezado Sr. Presidente da CPPD,",
        "(X) PROGRESSÃO FUNCIONAL POR DESEMPENHO ACADÊMICA/PROMOÇÃO",
        PARAGRAPH,
        "Em conformidade com a avaliação de desempenho em anexo, realizada na data de 02/04/2025.",
        "Belém, 10 de março de 2025.",
        "Nestes termos, pede deferimento.",
        "_" * 42,
        "Assinatura do (a) requerente",
        "Matrícula SIAPE: 1234567",
        "Observação",
        "De acordo com a Lei Geral de Proteção de Dados Pessoais (Lei nº 13.709/2018), "
        "deve-se restringir o acesso a este documento por conter informações pessoais.",
    ]


def test_the_request_paragraph_has_the_name_the_siape_and_the_interstice(tmp_path):
    found = texts(write(tmp_path, request_model()))

    paragraph = next(t for t in found if t.startswith("Eu, "))
    assert "Maria Docente da Silva" in paragraph
    assert "Matrícula SIAPE 1234567" in paragraph
    assert "23/11/2022 a 23/11/2024" in paragraph
    assert paragraph == PARAGRAPH


def test_the_blank_date_and_the_blank_city_are_written_as_they_are(tmp_path):
    found = texts(write(tmp_path, request_model(city=None, last_opinion=None)))

    assert (
        "Em conformidade com a avaliação de desempenho em anexo, realizada na data de ___/___/___."
        in found
    )
    assert "__________, 10 de março de 2025." in found


def test_the_header_the_title_and_the_signature_are_centered(tmp_path):
    document = Document(str(write(tmp_path, request_model())))

    by_text = {p.text: p for p in document.paragraphs}
    for text in (
        "MINISTÉRIO DA EDUCAÇÃO",
        "REQUERIMENTO DE PROGRESSÃO/PROMOÇÃO/REVISÃO - DOCENTES (MAGISTÉRIO SUPERIOR E EBTT)",
        "Assinatura do (a) requerente",
    ):
        assert by_text[text].alignment == 1  # WD_ALIGN_PARAGRAPH.CENTER
    assert by_text[PARAGRAPH].alignment == 3  # WD_ALIGN_PARAGRAPH.JUSTIFY


def test_control_characters_in_the_name_do_not_break_the_file(tmp_path):
    professor = replace(PROFESSOR, full_name="Maria\x00 Docente\x0b da Silva")

    found = texts(write(tmp_path, request_model(professor=professor)))

    assert any(t.startswith("Eu, Maria Docente da Silva, Matrícula") for t in found)


def test_there_is_no_paragraph_of_the_revision_part_of_the_model(tmp_path):
    found = texts(write(tmp_path, request_model()))

    others = [t for t in found if not t.startswith("REQUERIMENTO DE PROGRESSÃO/PROMOÇÃO/REVISÃO")]
    assert not any("revisão" in t.lower() for t in others)


def test_the_page_is_a4_with_the_margins_and_the_font_of_the_model(tmp_path):
    document = Document(str(write(tmp_path, request_model())))

    section = document.sections[0]
    assert (round(section.page_width.mm), round(section.page_height.mm)) == (210, 297)
    assert round(section.left_margin.mm, 2) == 30.0
    assert round(section.right_margin.mm, 2) == 20.0
    assert round(section.top_margin.mm, 2) == 30.0
    assert round(section.bottom_margin.mm, 2) == 20.0
    normal = document.styles["Normal"].font
    assert (normal.name, normal.size.pt) == ("Liberation Serif", 12)


def body_and_media(path):
    with zipfile.ZipFile(path) as archive:
        media = [n for n in archive.namelist() if n.startswith("word/media/")]
        return etree.fromstring(archive.read("word/document.xml")).find("w:body", NS), media


def test_the_first_element_is_the_centered_emblem_and_the_second_is_the_ministry(tmp_path):
    # BRAS-05, BRAS-06
    path = write(tmp_path, request_model())

    body, _ = body_and_media(path)
    first = body[0]
    assert first.tag == f"{{{W}}}p"
    assert first.find("w:pPr/w:jc", NS).get(f"{{{W}}}val") == "center"
    assert int(first.find(".//wp:inline/wp:extent", NS).get("cx")) == 720_000
    assert Document(str(path)).paragraphs[1].text == "MINISTÉRIO DA EDUCAÇÃO"


def test_the_package_has_a_single_image(tmp_path):
    # BRAS-07
    body, media = body_and_media(write(tmp_path, request_model()))

    assert len(media) == 1
    assert len(body.findall(".//w:drawing", NS)) == 1


def test_the_text_after_the_emblem_is_the_one_of_before(tmp_path):
    # BRAS-08: the paragraph of the emblem has no text, so the whole text is what it was
    found = [p.text for p in Document(str(write(tmp_path, request_model()))).paragraphs]

    assert found[0] == ""
    assert found[1:5] == [
        "MINISTÉRIO DA EDUCAÇÃO",
        "UNIVERSIDADE FEDERAL DO PARÁ",
        "PRÓ-REITORIA DE DESENVOLVIMENTO E GESTÃO DE PESSOAL",
        "REQUERIMENTO DE PROGRESSÃO/PROMOÇÃO/REVISÃO - DOCENTES (MAGISTÉRIO SUPERIOR E EBTT)",
    ]
    assert found[5] == "Prezado Sr. Presidente da CPPD,"
    assert found[-1].startswith("De acordo com a Lei Geral de Proteção de Dados Pessoais")


def test_without_the_emblem_file_the_writer_raises_and_writes_nothing(monkeypatch, tmp_path):
    # BRAS-10
    monkeypatch.setattr(emblem, "EMBLEM_FILE", tmp_path / "ufpa.png")
    target = tmp_path / "requerimento.docx"

    with pytest.raises(EmblemUnavailable):
        write_request_docx(request_model(), target)
    assert not target.exists()
