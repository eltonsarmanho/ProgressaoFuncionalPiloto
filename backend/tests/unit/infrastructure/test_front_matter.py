"""CMP-01, CMP-04: cover, table of contents and group separators of the Comprovante, each with
its own number at the foot (the cover has none)."""

from collections import defaultdict
from dataclasses import replace
from uuid import uuid4

import pymupdf
import pytest
from reportlab.lib.units import mm

from app.domain.entities.comprovante import (
    ComprovantePlan,
    PageKind,
    PlanPage,
    TocEntry,
    TocLevel,
)
from app.infrastructure.documents import emblem
from app.infrastructure.documents.emblem import EmblemUnavailable
from app.infrastructure.documents.front_matter import TOC_CAPACITY, write_front_matter
from tests.unit.domain.comprovante_support import make_activity
from tests.unit.infrastructure.comprovante_support import (
    attached_links,
    front,
    plan_for,
    plan_with_toc_lines,
)

FOOTER = "Comprovante p. "


def render(tmp_path, plan, document_names=None) -> pymupdf.Document:
    target = tmp_path / "front.pdf"
    write_front_matter(plan, front(document_names), target)
    return pymupdf.open(target)


def rows(page: pymupdf.Page) -> list[str]:
    """The text lines of a page, left to right, from the words that share a baseline."""
    lines: dict[int, list[tuple[float, str]]] = defaultdict(list)
    for x0, _y0, _x1, y1, word, *_ in page.get_text("words"):
        lines[round(y1)].append((x0, word))
    return [" ".join(w for _, w in sorted(found)) for _, found in sorted(lines.items())]


def generated(plan):
    return [p for p in plan.pages if p.kind is not PageKind.ORIGINAL]


def toc_pages(plan):
    return [p for p in plan.pages if p.kind is PageKind.SUMARIO]


def only_group_plan() -> ComprovantePlan:
    """One table-of-contents line: a group entry and nothing else."""
    pages = (
        PlanPage(PageKind.CAPA, 1),
        PlanPage(PageKind.SUMARIO, 2),
        PlanPage(PageKind.SEPARADOR, 3, 1),
    )
    return ComprovantePlan(pages, "h", (TocEntry(TocLevel.GRUPO, 1, first_page=3),))


@pytest.mark.parametrize("lines", [1, TOC_CAPACITY, TOC_CAPACITY + 1])
def test_the_table_of_contents_has_the_pages_the_plan_predicts(tmp_path, lines):
    plan = only_group_plan() if lines == 1 else plan_with_toc_lines(lines)[0]

    pdf = render(tmp_path, plan)

    expected = 2 if lines == TOC_CAPACITY + 1 else 1
    assert len(toc_pages(plan)) == expected
    assert len(pdf) == len(generated(plan))
    toc_numbers = [p.number for p in toc_pages(plan)]
    for page, plan_page in zip(pdf, generated(plan), strict=True):
        if plan_page.kind is PageKind.SUMARIO:
            assert f"{FOOTER}{plan_page.number}" in rows(page)[-1]
    assert toc_numbers == list(range(2, 2 + expected))


def test_every_entry_of_the_table_of_contents_shows_its_first_page(tmp_path):
    document_id = uuid4()
    one, two = make_activity(1, 1), make_activity(1, 1)
    links = attached_links(one, document_id, [3]) + attached_links(two, document_id, [5, 6])
    plan = plan_for([one, two], links)
    pdf = render(tmp_path, plan)

    shown = [line for line in rows(pdf[1]) if not line.startswith(FOOTER)]
    group, item, *activities = plan.toc
    # cover 1, table of contents 2, separator 3, then the originals from 4
    assert (group.first_page, item.first_page) == (3, 4)
    assert any(line.startswith("I. Ensino") and line.endswith(" 3") for line in shown)
    assert any(line.startswith("I.1 Aula de graduação") and line.endswith(" 4") for line in shown)
    for entry in activities:
        title_line = next(line for line in shown if line.startswith(entry.title))
        assert title_line.endswith(f" {entry.first_page}")
    assert [e.first_page for e in activities] == [4, 5]


def test_the_cover_has_no_number_and_the_other_generated_pages_have_their_own(tmp_path):
    first, second = make_activity(1, 1), make_activity(2, 3)
    plan = plan_for([first, second])
    pdf = render(tmp_path, plan)

    assert FOOTER not in pdf[0].get_text()
    for page, plan_page in zip(pdf[1:], generated(plan)[1:], strict=True):
        assert rows(page)[-1] == f"{FOOTER}{plan_page.number}"


def test_a_separator_has_only_the_title_of_its_group(tmp_path):
    plan = plan_for([make_activity(1, 1), make_activity(2, 3)])
    pdf = render(tmp_path, plan)

    separators = [
        page for page, p in zip(pdf, generated(plan), strict=True) if p.kind is PageKind.SEPARADOR
    ]
    assert [rows(page)[:-1] for page in separators] == [["I. Ensino"], ["II. Pesquisa"]]


def test_an_activity_takes_two_lines_with_its_origin_and_pages(tmp_path):
    activity = make_activity(1, 1, title="Aula de Cálculo")
    document_id = uuid4()
    plan = plan_for([activity], attached_links(activity, document_id, [4, 5]))
    pdf = render(tmp_path, plan, {document_id: "certificado.pdf"})

    shown = rows(pdf[1])
    start = next(i for i, line in enumerate(shown) if line.startswith("Aula de Cálculo"))
    first = plan.toc[-1].first_page
    assert shown[start].endswith(f" {first}")
    origin = "origem: certificado.pdf, p. 4; certificado.pdf, p. 5"
    assert shown[start + 1] == f"{origin} - Comprovante p. {first} a {first + 1}"


def test_an_activity_of_one_page_says_one_page_and_names_the_source_page_apart(tmp_path):
    activity = make_activity(1, 1, title="Aula de Álgebra")
    document_id = uuid4()
    plan = plan_for([activity], attached_links(activity, document_id, [9]))
    pdf = render(tmp_path, plan, {document_id: "declaracao.pdf"})

    shown = rows(pdf[1])
    start = next(i for i, line in enumerate(shown) if line.startswith("Aula de Álgebra"))
    first = plan.toc[-1].first_page
    assert first != 9  # the number in the Comprovante is not the page of the source document
    assert shown[start + 1] == f"origem: declaracao.pdf, p. 9 - Comprovante p. {first}"


def test_a_remission_and_an_activity_without_pages_are_written(tmp_path):
    one, two, none = make_activity(1, 1), make_activity(1, 1), make_activity(1, 1)
    document_id = uuid4()
    links = attached_links(one, document_id, [7]) + attached_links(two, document_id, [7])
    plan = plan_for([one, two, none], links)
    pdf = render(tmp_path, plan, {document_id: "a.pdf"})

    text = " ".join(rows(pdf[1]))
    assert f"ver comprovante nº {plan.toc[-3].first_page}, p. 7" in text
    assert "Sem comprovante anexado" in text


def test_the_cover_identifies_the_professor_class_level_unit_and_interstice(tmp_path):
    pdf = render(tmp_path, plan_for([make_activity(1, 1)]))

    text = " ".join(pdf[0].get_text().split())
    assert "Maria Docente da Silva" in text
    assert "Adjunto, nível 2" in text
    assert "Associado, nível 1" in text
    assert "Faculdade de Testes" in text
    assert "23/11/2022 a 23/11/2024" in text


def test_the_renderer_refuses_a_plan_whose_table_of_contents_has_another_size(tmp_path):
    plan, _ = plan_with_toc_lines(TOC_CAPACITY + 1)
    short = replace(
        plan, pages=tuple(p for p in plan.pages if p.kind is not PageKind.SUMARIO)[:1]
    )

    with pytest.raises(ValueError):
        render(tmp_path, short)


def test_a_title_longer_than_the_line_still_fits_on_one_line(tmp_path):
    activity = make_activity(1, 1, title="Título muito longo " * 20)
    plan = plan_for([activity])
    pdf = render(tmp_path, plan)

    shown = rows(pdf[1])
    start = next(i for i, line in enumerate(shown) if line.startswith("Título muito longo"))
    assert "…" in shown[start]
    assert shown[start].endswith(" —")  # no page: the number column is still at the end
    assert shown[start + 1] == "Sem comprovante anexado"


def emblem_rect(page: pymupdf.Page) -> pymupdf.Rect:
    images = page.get_images(full=True)
    assert len(images) == 1
    (rect,) = page.get_image_rects(images[0][0])
    return rect


def test_the_cover_has_the_emblem_centered_above_the_title_without_touching_it(tmp_path):
    # BRAS-03, BRAS-06
    pdf = render(tmp_path, plan_for([make_activity(1, 1)]))

    page = pdf[0]
    rect = emblem_rect(page)
    title = page.search_for("COMPROVANTE DE DOCUMENTOS")[0]
    assert rect.width == pytest.approx(20 * mm, abs=0.5)
    assert rect.height == pytest.approx(20 * mm * 351 / 279, abs=0.5)
    assert (rect.x0 + rect.x1) / 2 == pytest.approx(297.6, abs=0.5)  # half of the A4 width
    assert rect.y1 + 3 * mm <= title.y0


def test_only_the_cover_has_the_emblem_not_the_table_of_contents_nor_the_separators(tmp_path):
    # BRAS-03, BRAS-07
    plan, _ = plan_with_toc_lines(TOC_CAPACITY + 1)
    pdf = render(tmp_path, plan)
    kinds = [p.kind for p in generated(plan)]

    assert PageKind.SUMARIO in kinds and PageKind.SEPARADOR in kinds
    assert len(pdf[0].get_images()) == 1
    assert all(page.get_images() == [] for page in list(pdf)[1:])


def test_the_emblem_does_not_change_the_pages_nor_the_capacity_of_the_table_of_contents(tmp_path):
    # BRAS-03: the number of pages the plan predicted is the one written
    plan, _ = plan_with_toc_lines(TOC_CAPACITY)

    pdf = render(tmp_path, plan)

    assert TOC_CAPACITY == 44  # the capacity before the emblem
    assert len(toc_pages(plan)) == 1
    assert len(pdf) == len(generated(plan))
    assert f"{FOOTER}{toc_pages(plan)[0].number}" in rows(pdf[1])[-1]


def test_the_cover_text_is_the_one_of_before_and_has_no_number(tmp_path):
    # BRAS-08
    pdf = render(tmp_path, plan_for([make_activity(1, 1)]))

    shown = rows(pdf[0])
    assert shown[0] == "COMPROVANTE DE DOCUMENTOS"
    assert shown[1].startswith("Docente: Maria Docente da Silva")
    assert FOOTER not in pdf[0].get_text()


def test_without_the_emblem_file_the_front_matter_raises_and_writes_nothing(monkeypatch, tmp_path):
    # BRAS-10
    monkeypatch.setattr(emblem, "EMBLEM_FILE", tmp_path / "ufpa.png")
    target = tmp_path / "front.pdf"

    with pytest.raises(EmblemUnavailable):
        write_front_matter(plan_for([make_activity(1, 1)]), front(), target)
    assert not target.exists()
