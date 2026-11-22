"""PAR-03: the Parecer written as PDF with reportlab, with the same sections, order and text as
the DOCX of the same model (AD-011)."""

import re

import pymupdf

from app.domain.entities.board import BoardRole
from app.infrastructure.documents.opinion_docx import write_opinion_docx
from app.infrastructure.documents.opinion_pdf import write_opinion_pdf
from tests.unit.domain.board_document_support import member
from tests.unit.infrastructure.board_writer_support import opinion_model
from tests.unit.infrastructure.test_opinion_docx import body_texts

FOOTER = re.compile(r"Página \d+ de \d+")
SIGNATURE_RULE = "_" * 42


def render(tmp_path, model) -> pymupdf.Document:
    target = tmp_path / ".tmp-0123456789abcdef"  # the storage hands out a path with no extension
    write_opinion_pdf(model, target)
    return pymupdf.open(target, filetype="pdf")


def normalized(text: str) -> str:
    return " ".join(text.split())


def pdf_text(pdf) -> str:
    return normalized(FOOTER.sub(" ", " ".join(page.get_text() for page in pdf)))


def docx_text(tmp_path, model) -> str:
    target = tmp_path / "parecer.docx"
    write_opinion_docx(model, target)
    return normalized(" ".join(body_texts(target)))


def test_the_file_is_a_pdf_on_a4_written_at_the_given_path(tmp_path):
    target = tmp_path / ".tmp-0123456789abcdef"
    write_opinion_pdf(opinion_model(), target)

    assert target.read_bytes().startswith(b"%PDF")
    page = pymupdf.open(target, filetype="pdf")[0]
    assert (round(page.rect.width), round(page.rect.height)) == (595, 842)


def test_the_pdf_has_the_same_text_in_the_same_order_as_the_docx_of_the_model(tmp_path):
    model = opinion_model()

    text = pdf_text(render(tmp_path, model))

    assert text == docx_text(tmp_path, model)
    assert text.startswith("Serviço Público Federal Universidade Federal do Pará")


def test_the_sections_come_in_the_order_of_par_03(tmp_path):
    text = pdf_text(render(tmp_path, opinion_model()))

    positions = [
        text.index(heading)
        for heading in (
            "PARECER",
            "Identificação",
            "Docente: Maria Docente da Silva",
            "Portaria da banca: nº 123/2025, de 10/03/2025.",
            "Interstício",
            "Documentos analisados",
            "Pontuação por grupo",
            "I - Atividades de ensino 100,00",
            "Total geral 211,00",
            "Mínimo de referência: 200,00 pontos",
            "Conclusão",
            "A banca manifesta-se FAVORÁVEL",
            "Observações",
            "Belém, 02/04/2025",
            "Ana Presidente Souza",
        )
    ]
    assert positions == sorted(positions)
    assert len(set(positions)) == len(positions)


def test_the_total_geral_is_the_one_of_the_model(tmp_path):
    text = pdf_text(render(tmp_path, opinion_model()))

    assert "Total geral 211,00" in text


def test_three_members_give_three_signature_lines_with_name_and_role(tmp_path):
    text = pdf_text(render(tmp_path, opinion_model()))

    assert text.count(SIGNATURE_RULE) == 3
    assert text.endswith(
        f"{SIGNATURE_RULE} Ana Presidente Souza Presidente "
        f"{SIGNATURE_RULE} Bruno Membro Lima Membro "
        f"{SIGNATURE_RULE} Carla Suplente Reis Suplente"
    )


def test_many_members_take_a_second_page_and_every_page_has_its_footer(tmp_path):
    members = tuple(member(f"Membro Sintético {n:02d}", BoardRole.MEMBRO) for n in range(15))

    pdf = render(tmp_path, opinion_model(members=members))

    assert len(pdf) >= 2
    for number, page in enumerate(pdf, start=1):
        assert f"Página {number} de {len(pdf)}" in normalized(page.get_text())
    assert pdf_text(pdf).count(SIGNATURE_RULE) == 15


def test_control_characters_do_not_come_out_as_boxes_and_markup_comes_out_as_written(tmp_path):
    members = (member("Ana\x00 <b>Souza</b> &\x0b", BoardRole.PRESIDENTE),)
    model = opinion_model(members=members, notes="Linha um\x00\x0b\nLinha <dois> & ü")

    text = pdf_text(render(tmp_path, model))

    assert "Ana <b>Souza</b> &" in text
    assert "Linha um Linha <dois> & ü" in text
    assert "\x00" not in text and "\x0b" not in text


def test_only_the_liberation_serif_faces_are_listed(tmp_path):
    pdf = render(tmp_path, opinion_model())

    names = {font[3].split("+")[-1] for page in pdf for font in page.get_fonts()}
    assert names
    assert names <= {
        "LiberationSerif", "LiberationSerif-Bold", "LiberationSerif-Italic",
        "LiberationSerif-BoldItalic",
    }  # fmt: skip


def test_the_text_stays_inside_the_margins_of_the_model(tmp_path):
    page = render(tmp_path, opinion_model())[0]

    left, right = 30.0 / 25.4 * 72, 20.0 / 25.4 * 72
    blocks = [b for b in page.get_text("blocks") if not FOOTER.search(b[4])]
    assert min(b[0] for b in blocks) >= left - 1
    assert max(b[2] for b in blocks) <= 595 - right + 1
