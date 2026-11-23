"""PMOD-01, PMOD-02, PMOD-04 to PMOD-07, PMOD-13, PMOD-19, PMOD-20, PMOD-21: the Parecer written
as PDF with reportlab, with the same text in the same order as the DOCX of the same model
(AD-011)."""

import pymupdf
import pytest
from reportlab.lib.units import mm

from app.domain.entities.board import BoardRole
from app.infrastructure.documents import emblem
from app.infrastructure.documents.emblem import EmblemUnavailable
from app.infrastructure.documents.opinion_docx import write_opinion_docx
from app.infrastructure.documents.opinion_pdf import write_opinion_pdf
from tests.unit.domain.board_document_support import MEMBERS, member
from tests.unit.infrastructure.board_writer_support import opinion_model
from tests.unit.infrastructure.test_opinion_docx import THREE_TITULARS, body_texts

LEFT = 30.0 / 25.4 * 72  # margins of the model, in points
RIGHT = 20.0 / 25.4 * 72
PAGE_WIDTH = 595.276


def render(tmp_path, model) -> pymupdf.Document:
    target = tmp_path / ".tmp-0123456789abcdef"  # the storage hands out a path with no extension
    write_opinion_pdf(model, target)
    return pymupdf.open(target, filetype="pdf")


def normalized(text: str) -> str:
    return " ".join(text.split())


def pdf_text(pdf) -> str:
    return normalized(" ".join(page.get_text() for page in pdf))


def docx_text(tmp_path, model) -> str:
    target = tmp_path / "parecer.docx"
    write_opinion_docx(model, target)
    return normalized(" ".join(body_texts(target)))


def spans(page) -> list[tuple[str, str]]:
    """(face without the subset tag, text) of every span of the page, in reading order."""
    found = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            found.extend((s["font"].split("+")[-1], s["text"]) for s in line["spans"])
    return found


def test_the_file_is_a_pdf_on_a4_written_at_the_given_path(tmp_path):
    target = tmp_path / ".tmp-0123456789abcdef"
    write_opinion_pdf(opinion_model(), target)

    assert target.read_bytes().startswith(b"%PDF")
    page = pymupdf.open(target, filetype="pdf")[0]
    assert (round(page.rect.width), round(page.rect.height)) == (595, 842)


def test_the_text_comes_in_the_order_of_the_model(tmp_path):
    text = pdf_text(render(tmp_path, opinion_model()))

    markers = [
        "Universidade Federal do Pará",
        "Campus Universitário Sintético",
        "Faculdade de Testes Sintéticos – FATS",
        "PARECER",
        "Belém, 2 de Abril de 2025.",
        "Aos dois dias do mês de abril de dois mil e vinte e cinco, reuniram-se os membros",
        "responsáveis por analisar o Relatório de Atividades do Professor Adjunto Nível IV Maria",
        "Após a análise, os membros APROVARAM o referido relatório.",
        "PRESIDENTE: Ana Presidente Souza",
        "MEMBRO 1: Bruno Membro Lima",
    ]
    positions = [text.index(marker) for marker in markers]
    assert positions == sorted(positions)
    assert text.endswith("MEMBRO 1: Bruno Membro Lima")
    assert "Carla Suplente Reis" not in text


def test_the_pdf_has_the_same_text_in_the_same_order_as_the_docx_of_the_model(tmp_path):
    model = opinion_model()

    assert pdf_text(render(tmp_path, model)) == docx_text(tmp_path, model)


def test_the_pdf_has_the_same_text_as_the_docx_without_a_campus_and_without_a_president(tmp_path):
    members = (member("Bruno Membro Lima"), member("Carla Membro Reis"))
    model = opinion_model(members=members, parent_unit=None, opinion_date=None, place=None)

    assert pdf_text(render(tmp_path, model)) == docx_text(tmp_path, model)


def test_three_titular_members_fit_on_a_single_page(tmp_path):
    pdf = render(tmp_path, opinion_model(members=THREE_TITULARS))

    assert len(pdf) == 1
    assert "MEMBRO 2: Carla Membro Reis" in pdf_text(pdf)


def test_with_an_alternate_besides_the_titulars_the_pdf_is_still_a_single_page(tmp_path):
    members = (*THREE_TITULARS, member("Davi Suplente Rocha", BoardRole.SUPLENTE))

    pdf = render(tmp_path, opinion_model(members=members))

    assert len(pdf) == 1
    assert "Davi Suplente Rocha" not in pdf_text(pdf)


def test_fifteen_members_with_names_of_two_hundred_characters_take_more_pages_and_all_appear(
    tmp_path,
):
    names = [(f"Membro {n:02d} " + "Sobrenome " * 20)[:199] + "z" for n in range(15)]
    members = tuple(member(name, BoardRole.MEMBRO) for name in names)
    model = opinion_model(members=members)

    pdf = render(tmp_path, model)

    assert len(pdf) > 1
    text = pdf_text(pdf)
    for number, name in enumerate(names, start=1):
        assert f"MEMBRO {number}: {normalized(name)}" in text
        assert len(name) == 200
    assert text == docx_text(tmp_path, model)


def test_the_date_words_and_the_current_situation_with_the_name_are_bold_and_aos_is_not(tmp_path):
    found = spans(render(tmp_path, opinion_model())[0])

    bold = [text for face, text in found if face == "LiberationSerif-Bold"]
    assert "dois dias do mês de abril de dois mil e vinte e cinco" in " ".join(bold)
    assert "Adjunto Nível IV Maria Docente da Silva" in " ".join(bold)
    assert any(face == "LiberationSerif" and text.startswith("Aos") for face, text in found)
    assert not any(face == "LiberationSerif-Bold" and "Aos" in text for face, text in found)
    assert not any(face == "LiberationSerif-Bold" and "Professor" in text for face, text in found)


def test_the_title_and_the_place_and_date_line_are_sans_and_the_rest_is_serif(tmp_path):
    found = spans(render(tmp_path, opinion_model())[0])

    assert ("LiberationSans-Bold", "PARECER") in found
    sans = [text for face, text in found if face == "LiberationSans"]
    assert "".join(sans).strip() == "Belém, 2 de Abril de 2025."
    serif_text = " ".join(text for face, text in found if face.startswith("LiberationSerif"))
    for text in ("Universidade Federal do Pará", "PRESIDENTE: Ana Presidente Souza", "Aos "):
        assert text.strip() in serif_text
    assert "PARECER" not in serif_text and "Belém" not in serif_text


def test_only_the_liberation_faces_are_listed(tmp_path):
    pdf = render(tmp_path, opinion_model())

    names = {font[3].split("+")[-1] for page in pdf for font in page.get_fonts()}
    assert names == {
        "LiberationSerif",
        "LiberationSerif-Bold",
        "LiberationSans",
        "LiberationSans-Bold",
    }


def test_the_place_and_date_line_starts_at_half_the_text_width(tmp_path):
    page = render(tmp_path, opinion_model())[0]

    word = next(w for w in page.get_text("words") if w[4] == "Belém,")
    assert word[0] == pytest.approx(LEFT + (PAGE_WIDTH - LEFT - RIGHT) / 2, abs=1.5)


def test_a_horizontal_rule_crosses_the_text_width_under_the_header(tmp_path):
    page = render(tmp_path, opinion_model())[0]

    rules = [
        item
        for drawing in page.get_drawings()
        for item in drawing["items"]
        if item[0] == "l" and abs(item[1].y - item[2].y) < 0.01
    ]
    assert len(rules) == 1
    start, end = rules[0][1], rules[0][2]
    assert min(start.x, end.x) == pytest.approx(LEFT, abs=1)
    assert max(start.x, end.x) == pytest.approx(PAGE_WIDTH - RIGHT, abs=1)
    last_header = max(w[3] for w in page.get_text("words") if w[4] == "FATS")
    title = min(w[1] for w in page.get_text("words") if w[4] == "PARECER")
    assert last_header <= start.y <= title


def test_the_paragraph_is_indented_on_its_first_line_only(tmp_path):
    page = render(tmp_path, opinion_model())[0]

    lines = [
        (line["bbox"][0], "".join(s["text"] for s in line["spans"]))
        for block in page.get_text("dict")["blocks"]
        for line in block.get("lines", [])
    ]
    first = next(x for x, text in lines if text.startswith("Aos "))
    others = [x for x, text in lines if text.startswith(("Banca", "Professor", "de ", "para"))]
    assert first == pytest.approx(LEFT + 1.25 / 2.54 * 72, abs=1)
    assert others
    assert all(x == pytest.approx(LEFT, abs=1) for x in others)


def text_lines(page: pymupdf.Page) -> list[tuple[pymupdf.Rect, float, str]]:
    """(box, font size, text) of every text line of the page, top to bottom."""
    return [
        (
            pymupdf.Rect(line["bbox"]),
            max(s["size"] for s in line["spans"]),
            "".join(s["text"] for s in line["spans"]),
        )
        for block in page.get_text("dict")["blocks"]
        for line in block.get("lines", [])
    ]


def paragraph_lines(page: pymupdf.Page) -> list[tuple[pymupdf.Rect, float, str]]:
    """The lines of the single paragraph: between the place and date line and the first member."""
    lines = text_lines(page)
    top = next(box.y1 for box, _, text in lines if text.startswith("Belém,"))
    bottom = next(box.y0 for box, _, text in lines if text.startswith("PRESIDENTE:"))
    return [line for line in lines if top <= line[0].y0 and line[0].y1 <= bottom]


def test_the_header_the_title_and_the_member_lines_are_centered_on_the_text_area(tmp_path):
    # PMOD-02, PMOD-04, PMOD-13
    page = render(tmp_path, opinion_model())[0]
    center = (LEFT + PAGE_WIDTH - RIGHT) / 2

    wanted = [
        "Universidade Federal do Pará",
        "Campus Universitário Sintético",
        "Faculdade de Testes Sintéticos – FATS",
        "PARECER",
        "PRESIDENTE: Ana Presidente Souza",
        "MEMBRO 1: Bruno Membro Lima",
    ]
    lines = {text: box for box, _, text in text_lines(page)}
    for text in wanted:
        box = lines[text]
        assert (box.x0 + box.x1) / 2 == pytest.approx(center, abs=1.5), text


def test_the_paragraph_is_justified_up_to_its_last_line(tmp_path):
    # PMOD-06
    lines = paragraph_lines(render(tmp_path, opinion_model())[0])

    assert len(lines) > 2
    for box, _, text in lines[:-1]:
        assert box.x1 == pytest.approx(PAGE_WIDTH - RIGHT, abs=1.5), text
    assert lines[-1][0].x1 < PAGE_WIDTH - RIGHT - 20


def test_the_paragraph_is_set_in_12_pt_with_one_and_a_half_line_spacing(tmp_path):
    # PMOD-06, assumption "Fontes do Parecer": 12 pt body, spacing 1.5 (12 x 1.5 = 18 pt)
    page = render(tmp_path, opinion_model())[0]
    lines = paragraph_lines(page)

    assert len(lines) > 2
    assert {size for _, size, _ in lines} == {12.0}
    pitches = [b[0].y0 - a[0].y0 for a, b in zip(lines, lines[1:], strict=False)]
    assert pitches == [pytest.approx(18.0, abs=0.5)] * len(pitches)
    assert {size for _, size, _ in text_lines(page)} == {12.0}


def test_there_is_no_page_footer_and_no_table(tmp_path):
    pdf = render(tmp_path, opinion_model())

    assert "Página" not in pdf_text(pdf)
    assert not pdf[0].find_tables().tables


def test_control_characters_do_not_come_out_as_boxes_and_markup_comes_out_as_written(tmp_path):
    members = (member("Ana\x00 <b>Souza</b> &\x0b", BoardRole.PRESIDENTE),)

    text = pdf_text(render(tmp_path, opinion_model(members=members)))

    assert "PRESIDENTE: Ana <b>Souza</b> &" in text
    assert "Ana <b>Souza</b> & (presidente)" in text
    assert "\x00" not in text and "\x0b" not in text


def test_the_text_stays_inside_the_margins_of_the_model(tmp_path):
    page = render(tmp_path, opinion_model(members=MEMBERS))[0]

    blocks = page.get_text("blocks")
    assert min(b[0] for b in blocks) >= LEFT - 1
    assert max(b[2] for b in blocks) <= PAGE_WIDTH - RIGHT + 1


def emblem_rect(page: pymupdf.Page) -> pymupdf.Rect:
    images = page.get_images(full=True)
    assert len(images) == 1
    (rect,) = page.get_image_rects(images[0][0])
    return rect


def test_the_first_page_has_the_emblem_centered_on_the_text_above_the_university(tmp_path):
    # BRAS-04, BRAS-06
    page = render(tmp_path, opinion_model())[0]

    rect = emblem_rect(page)
    assert rect.width == pytest.approx(20 * mm, abs=0.5)
    assert rect.height == pytest.approx(20 * mm * 351 / 279, abs=0.5)
    assert (rect.x0 + rect.x1) / 2 == pytest.approx((LEFT + PAGE_WIDTH - RIGHT) / 2, abs=0.5)
    university = page.search_for("Universidade Federal do Pará")[0]
    assert rect.y1 + 3 * mm <= university.y0


def test_with_three_titulars_and_a_campus_the_parecer_with_the_emblem_is_one_page(tmp_path):
    # PMOD-21
    pdf = render(tmp_path, opinion_model(members=THREE_TITULARS))

    assert len(pdf) == 1
    assert len(pdf[0].get_images()) == 1
    assert "MEMBRO 2: Carla Membro Reis" in pdf_text(pdf)


def test_with_fifteen_members_only_the_first_page_has_the_emblem(tmp_path):
    # BRAS-07
    names = [(f"Membro {n:02d} " + "Sobrenome " * 20)[:199] + "z" for n in range(15)]
    members = tuple(member(name, BoardRole.MEMBRO) for name in names)

    pdf = render(tmp_path, opinion_model(members=members))

    assert len(pdf) > 1
    assert len(pdf[0].get_images()) == 1
    assert all(page.get_images() == [] for page in list(pdf)[1:])


def test_the_text_with_the_emblem_is_the_one_of_the_docx_and_adds_no_font(tmp_path):
    # BRAS-08
    model = opinion_model(members=THREE_TITULARS)

    pdf = render(tmp_path, model)

    assert pdf_text(pdf) == docx_text(tmp_path, model)
    names = {font[3].split("+")[-1] for page in pdf for font in page.get_fonts()}
    assert names == {
        "LiberationSerif",
        "LiberationSerif-Bold",
        "LiberationSans",
        "LiberationSans-Bold",
    }


def test_without_the_emblem_file_the_writer_raises_and_writes_nothing(monkeypatch, tmp_path):
    # BRAS-10
    monkeypatch.setattr(emblem, "EMBLEM_FILE", tmp_path / "ufpa.png")
    target = tmp_path / "parecer.pdf"

    with pytest.raises(EmblemUnavailable):
        write_opinion_pdf(opinion_model(), target)
    assert not target.exists()
