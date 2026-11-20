"""REL-09, REL-11, REL-12: the activities report written as DOCX with python-docx."""

import zipfile
from dataclasses import replace

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from lxml import etree

from app.domain.entities.report import DocumentGroup, DocumentSection
from app.infrastructure.documents.report_docx import write_report_docx
from tests.unit.domain.test_table_document_totals import HEADER
from tests.unit.infrastructure.report_model_support import report_document, synthetic_activities

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}


def write(tmp_path, model):
    target = tmp_path / "relatorio.docx"
    write_report_docx(model, target)
    return target


def paragraphs(path) -> list[str]:
    return [p.text for p in Document(str(path)).paragraphs]


def has_lines(texts: list[str], entry: str) -> bool:
    """The lines of the entry come as consecutive paragraphs."""
    lines = entry.split("\n")
    return any(texts[i : i + len(lines)] == lines for i in range(len(texts)))


def test_the_document_opens_with_the_institutional_header_centered_then_the_title(tmp_path):
    document = Document(str(write(tmp_path, report_document())))

    first = document.paragraphs[:3]
    assert [p.text for p in first] == [
        "Serviço Público Federal",
        "Universidade Federal do Pará",
        "Faculdade de Testes",
    ]
    assert all(p.alignment == WD_ALIGN_PARAGRAPH.CENTER for p in first)
    texts = [p.text for p in document.paragraphs]
    title = texts.index("RELATÓRIO DE ATIVIDADES")
    assert title > 2
    assert document.paragraphs[title].alignment == WD_ALIGN_PARAGRAPH.CENTER


def test_the_identification_names_the_professor_the_class_the_unit_and_the_interstice(tmp_path):
    texts = paragraphs(write(tmp_path, report_document()))

    assert "Nome: Maria Docente da Silva" in texts
    assert "Professor Adjunto, nível 2" in texts
    assert "Unidade: Faculdade de Testes" in texts
    assert "Período de interstício: 23/11/2022 a 23/11/2024" in texts
    heading = texts.index("ATIVIDADES DESENVOLVIDAS")
    assert heading > texts.index("Período de interstício: 23/11/2022 a 23/11/2024")


def test_every_section_with_activity_is_there_in_the_order_of_the_template_and_the_empty_are_not(
    tmp_path,
):
    texts = paragraphs(write(tmp_path, report_document()))

    headings = [
        t
        for t in texts
        if t[:3] in {"1.1", "1.2", "1.3"} or t[:2] in {"2 ", "3 ", "4 ", "5 ", "6 "}
    ]
    assert headings == [
        "1.1 Atividades didáticas: graduação",
        "1.3 Atividades didáticas: orientações",
        "2 Pesquisa",
        "3 Extensão",
        "6 Outras atividades",
    ]


def test_the_text_of_each_entry_is_the_text_of_the_draft_with_its_subtitle(tmp_path):
    model = report_document()
    texts = paragraphs(write(tmp_path, model))

    for section in model.sections:
        for group in section.groups:
            if group.subtitle:
                assert group.subtitle in texts
            for entry in group.entries:
                assert has_lines(texts, entry)
    assert "1º Período de 2023" in texts
    assert "2º Período de 2023" in texts
    assert has_lines(
        texts, "Disciplina: Cálculo Diferencial\nCarga horária: 60 h\nPeríodo: 1º Período de 2023"
    )


def test_nothing_is_added_beyond_the_header_the_titles_the_subtitles_and_the_draft(tmp_path):
    model = report_document()
    texts = paragraphs(write(tmp_path, model))

    expected = {
        *model.header_lines,
        model.title,
        *model.identification,
        model.body_heading,
        "",
    }
    for section in model.sections:
        expected.add(f"{section.key} {section.title}")
        for group in section.groups:
            expected.update(filter(None, [group.subtitle]))
            for entry in group.entries:
                expected.update(entry.split("\n"))
    assert set(texts) <= expected
    joined = " ".join(texts).lower()
    for word in ("objetivo", "resultado", "metodologia"):
        assert word not in joined


def test_typed_text_of_a_section_is_written_before_its_entries(tmp_path):
    model = report_document()
    section = model.sections[2]
    typed = replace(section, free_text="Texto digitado pelo docente para a seção.")
    model = replace(model, sections=(*model.sections[:2], typed, *model.sections[3:]))

    texts = paragraphs(write(tmp_path, model))

    at = texts.index(f"{section.key} {section.title}")
    assert texts[at + 1] == "Texto digitado pelo docente para a seção."


def test_the_page_is_a4_with_the_margins_and_the_font_of_the_model(tmp_path):
    document = Document(str(write(tmp_path, report_document())))

    section = document.sections[0]
    assert (round(section.page_width.mm), round(section.page_height.mm)) == (210, 297)
    assert round(section.left_margin.mm, 2) == 31.75
    assert round(section.right_margin.mm, 2) == 31.75
    assert round(section.top_margin.mm, 2) == 25.4
    assert round(section.bottom_margin.mm, 2) == 25.4
    normal = document.styles["Normal"].font
    assert (normal.name, normal.size.pt) == ("Times New Roman", 9)


def test_entries_are_justified_bullets_and_the_footer_has_the_page_fields(tmp_path):
    path = write(tmp_path, report_document())

    body = Document(str(path)).paragraphs
    first = [p for p in body if p.text.startswith("Disciplina:")]
    rest = [p for p in body if p.text.startswith("Carga horária:")]
    assert first and rest
    assert all(p.alignment == WD_ALIGN_PARAGRAPH.JUSTIFY for p in first + rest)
    assert all(p.style.name == "List Bullet" for p in first)
    assert all(p.style.name != "List Bullet" for p in rest)
    footers = [n for n in zipfile.ZipFile(path).namelist() if n.startswith("word/footer")]
    footer = etree.fromstring(zipfile.ZipFile(path).read(footers[0]))
    assert [t.text.strip() for t in footer.findall(".//w:instrText", NS)] == ["PAGE", "NUMPAGES"]


def test_accents_characters_outside_basic_latin_and_control_characters_are_written_safely(tmp_path):
    header = replace(HEADER, professor_name="Zoë Ñandú ª ü ç Łukasz Ωμέγα 日本語")
    model = report_document(header=header)
    group = DocumentGroup(
        "Subtítulo ç", ("Linha com Ação e controle\x00\x0b fim\nSegunda linha ü",)
    )
    model = replace(model, sections=(DocumentSection("2", "Pesquisa", "", (group,)),))

    texts = paragraphs(write(tmp_path, model))

    assert "Nome: Zoë Ñandú ª ü ç Łukasz Ωμέγα 日本語" in texts
    assert "Subtítulo ç" in texts
    assert has_lines(texts, "Linha com Ação e controle fim\nSegunda linha ü")


def test_a_document_with_no_section_still_writes_the_header_and_the_identification(tmp_path):
    texts = paragraphs(write(tmp_path, report_document(activities=[])))

    assert "RELATÓRIO DE ATIVIDADES" in texts
    assert "ATIVIDADES DESENVOLVIDAS" in texts
    assert not any(t[:3] == "1.1" for t in texts)


def test_a_hundred_sections_worth_of_entries_are_written(tmp_path):
    activities = synthetic_activities(
        extra=[a for _ in range(100) for a in synthetic_activities()[3:4]]
    )

    texts = paragraphs(write(tmp_path, report_document(activities)))

    assert len([t for t in texts if t.startswith("Título: Projeto de pesquisa")]) == 101
