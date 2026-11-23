"""REL-09, REL-11: the activities report written as PDF with reportlab, with the same sections,
order and text as the DOCX of the same model."""

import re
from dataclasses import replace

import pymupdf
import pytest
from docx import Document
from reportlab.lib.units import mm

from app.domain.entities.report import DocumentGroup, DocumentSection
from app.infrastructure.documents import emblem
from app.infrastructure.documents.emblem import EmblemUnavailable
from app.infrastructure.documents.report_docx import write_report_docx
from app.infrastructure.documents.report_pdf import write_report_pdf
from tests.unit.domain.test_table_document_totals import HEADER
from tests.unit.infrastructure.report_model_support import report_document, synthetic_activities

FOOTER = re.compile(r"Página \d+ de \d+")


def render(tmp_path, model) -> pymupdf.Document:
    target = tmp_path / "relatorio.pdf"
    write_report_pdf(model, target)
    return pymupdf.open(target)


def normalized(text: str) -> str:
    return " ".join(text.split())


def pdf_text(pdf) -> str:
    """The text without the page footers and without the bullets."""
    text = " ".join(page.get_text() for page in pdf)
    return normalized(FOOTER.sub(" ", text).replace("•", " "))


def docx_text(tmp_path, model) -> str:
    target = tmp_path / "relatorio.docx"
    write_report_docx(model, target)
    return normalized(" ".join(p.text for p in Document(str(target)).paragraphs))


def test_the_pdf_has_the_same_text_in_the_same_order_as_the_docx_of_the_model(tmp_path):
    model = report_document()

    assert pdf_text(render(tmp_path, model)) == docx_text(tmp_path, model)


def test_the_same_holds_for_a_long_report_that_takes_several_pages(tmp_path):
    activities = synthetic_activities(
        extra=[a for _ in range(120) for a in synthetic_activities()[3:5]]
    )
    model = report_document(activities)

    pdf = render(tmp_path, model)

    assert len(pdf) > 2
    assert pdf_text(pdf) == docx_text(tmp_path, model)


def test_the_sections_come_in_the_order_of_the_template_and_the_empty_ones_are_not_there(tmp_path):
    text = pdf_text(render(tmp_path, report_document()))

    positions = [
        text.index(title)
        for title in (
            "1.1 Atividades didáticas: graduação",
            "1.3 Atividades didáticas: orientações",
            "2 Pesquisa",
            "3 Extensão",
            "6 Outras atividades",
        )
    ]
    assert positions == sorted(positions)
    assert "1.2 " not in text
    assert "4 Administração" not in text
    assert "5 Atividades culturais" not in text


def test_the_header_the_identification_and_the_typed_text_are_written(tmp_path):
    model = report_document()
    typed = replace(model.sections[2], free_text="Texto digitado pelo docente para a seção.")
    model = replace(model, sections=(*model.sections[:2], typed, *model.sections[3:]))

    text = pdf_text(render(tmp_path, model))

    for part in (
        "Serviço Público Federal Universidade Federal do Pará Faculdade de Testes",
        "RELATÓRIO DE ATIVIDADES",
        "Nome: Maria Docente da Silva",
        "Professor Adjunto, nível 2",
        "Período de interstício: 23/11/2022 a 23/11/2024",
        "ATIVIDADES DESENVOLVIDAS",
        "2 Pesquisa Texto digitado pelo docente para a seção.",
    ):
        assert part in text


def test_nothing_is_added_to_the_text_of_the_draft(tmp_path):
    text = pdf_text(render(tmp_path, report_document())).lower()

    for word in ("objetivo", "resultado", "metodologia"):
        assert word not in text


def test_the_page_is_a4_with_the_margins_of_the_model(tmp_path):
    pdf = render(tmp_path, report_document())

    page = pdf[0]
    assert (round(page.rect.width), round(page.rect.height)) == (595, 842)
    left = 31.75 / 25.4 * 72
    top = 25.4 / 25.4 * 72
    blocks = [b for b in page.get_text("blocks") if not FOOTER.search(b[4])]
    assert min(b[0] for b in blocks) >= left - 1
    assert max(b[2] for b in blocks) <= 595 - left + 1
    assert min(b[1] for b in blocks) >= top - 1


def test_every_page_has_its_footer_as_page_n_of_m(tmp_path):
    activities = synthetic_activities(
        extra=[a for _ in range(120) for a in synthetic_activities()[3:5]]
    )

    pdf = render(tmp_path, report_document(activities))

    for number, page in enumerate(pdf, start=1):
        assert f"Página {number} de {len(pdf)}" in normalized(page.get_text())


def test_each_entry_starts_with_a_bullet_and_the_text_is_in_liberation_serif(tmp_path):
    model = report_document()
    pdf = render(tmp_path, model)

    entries = sum(len(g.entries) for s in model.sections for g in s.groups)
    assert " ".join(p.get_text() for p in pdf).count("•") == entries
    names = {font[3].split("+")[-1] for font in pdf[0].get_fonts()}
    assert names <= {
        "LiberationSerif", "LiberationSerif-Bold", "LiberationSerif-Italic",
        "LiberationSerif-BoldItalic",
    }  # fmt: skip


def test_accents_latin_extended_letters_and_markup_characters_come_out_as_written(tmp_path):
    header = replace(HEADER, professor_name="Zoë Ñandú ª ü ç Łukasz Őrdög Žižek")
    group = DocumentGroup("Subtítulo ç", ("Linha com Ação, <b> & controle\x00\x0b fim\nSegunda ü",))
    model = replace(
        report_document(header=header),
        sections=(DocumentSection("2", "Pesquisa", "", (group,)),),
    )

    text = pdf_text(render(tmp_path, model))

    assert "Nome: Zoë Ñandú ª ü ç Łukasz Őrdög Žižek" in text
    assert "Subtítulo ç" in text
    assert "Linha com Ação, <b> & controle fim Segunda ü" in text


def test_a_report_with_no_section_still_has_the_header_and_the_identification(tmp_path):
    text = pdf_text(render(tmp_path, report_document(activities=[])))

    assert "RELATÓRIO DE ATIVIDADES" in text
    assert "ATIVIDADES DESENVOLVIDAS" in text


def emblem_rect(page: pymupdf.Page) -> pymupdf.Rect:
    images = page.get_images(full=True)
    assert len(images) == 1
    (rect,) = page.get_image_rects(images[0][0])
    return rect


def test_the_first_page_has_the_emblem_centered_on_the_text_above_the_header(tmp_path):
    # BRAS-02, BRAS-06
    model = report_document()
    page = render(tmp_path, model)[0]

    rect = emblem_rect(page)
    layout = model.layout.page
    text_center = (
        layout.margin_left_mm * mm + (page.rect.width - layout.margin_right_mm * mm)
    ) / 2
    assert rect.width == pytest.approx(20 * mm, abs=0.5)
    assert rect.height == pytest.approx(20 * mm * 351 / 279, abs=0.5)
    assert (rect.x0 + rect.x1) / 2 == pytest.approx(text_center, abs=0.5)
    first_line = page.search_for("Serviço Público Federal")[0]
    assert rect.y1 + 3 * mm <= first_line.y0


def test_only_the_first_page_of_a_long_report_has_the_emblem(tmp_path):
    # BRAS-07
    activities = synthetic_activities(
        extra=[a for _ in range(120) for a in synthetic_activities()[3:5]]
    )
    pdf = render(tmp_path, report_document(activities))

    assert len(pdf) > 2
    assert len(pdf[0].get_images()) == 1
    assert all(page.get_images() == [] for page in list(pdf)[1:])


def test_without_the_emblem_file_the_writer_raises_and_writes_nothing(monkeypatch, tmp_path):
    # BRAS-10
    monkeypatch.setattr(emblem, "EMBLEM_FILE", tmp_path / "ufpa.png")
    target = tmp_path / "relatorio.pdf"

    with pytest.raises(EmblemUnavailable):
        write_report_pdf(report_document(), target)
    assert not target.exists()
