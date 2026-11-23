"""BRAS-01 to BRAS-05, BRAS-06, BRAS-07, BRAS-10, BRAS-11, PMOD-19, PMOD-20, PMOD-24: the five
generated documents of a synthetic process carry the emblem, the Parecer follows the official
model, no generation produces a file without the emblem, and an old version never changes."""

import hashlib
import logging
import zipfile

import pymupdf
import pytest
from lxml import etree
from reportlab.lib.units import mm

from app.domain.entities.generated import (
    DocumentFormat,
    DocumentKind,
    GenerationCode,
    GenerationState,
)
from app.infrastructure.documents import emblem
from app.infrastructure.documents.config_loader import load_report_config
from tests.integration.doc_usecases.board_support import add_typed_ordinance
from tests.integration.doc_usecases.opinion_support import (
    add_opinion,
    ask,
    ready,
    ready_table,
    run_one,
)
from tests.integration.doc_usecases.test_run_generation_opinion import (
    file_path,
    flat_texts,
    stored_files,
)

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W, "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"}
EMBLEM_WIDTH_PT = 20 * mm
EMBLEM_WIDTH_EMU = 720_000  # 2.0 cm
EMBLEM_RATIO = 351 / 279
FIXED_MESSAGE = "Erro interno ao gerar o documento. Tente gerar de novo."
FIVE = (
    DocumentKind.TABELA,
    DocumentKind.RELATORIO,
    DocumentKind.COMPROVANTE,
    DocumentKind.REQUERIMENTO,
    DocumentKind.PARECER,
)
WITH_DOCX = tuple(kind for kind in FIVE if kind is not DocumentKind.COMPROVANTE)


@pytest.fixture
def five(gen):
    """A synthetic process with the five documents generated, each in its version 1."""
    table = ready_table(gen)
    add_typed_ordinance(gen.world)
    add_opinion(gen.world)
    return {DocumentKind.TABELA: table, **{kind: ready(gen, kind) for kind in FIVE[1:]}}


def text_center(kind: DocumentKind, page: pymupdf.Page) -> float:
    """Where the middle of the text width of the page is, from the margins of the model."""
    if kind in (DocumentKind.TABELA, DocumentKind.COMPROVANTE):
        return page.rect.width / 2  # symmetric margins
    layout = load_report_config().layout.page
    return (layout.margin_left_mm * mm + page.rect.width - layout.margin_right_mm * mm) / 2


def docx_body(path):
    with zipfile.ZipFile(path) as archive:
        media = {n: archive.read(n) for n in archive.namelist() if n.startswith("word/media/")}
        return etree.fromstring(archive.read("word/document.xml")).find("w:body", NS), media


# --- the emblem on the five documents (BRAS-01 to BRAS-07) --------------------------------------


@pytest.mark.parametrize("kind", WITH_DOCX)
def test_every_docx_has_the_png_and_opens_with_its_paragraph_centered_and_two_centimeters_wide(
    gen, five, kind
):
    body, media = docx_body(file_path(gen, five[kind], DocumentFormat.DOCX))

    assert list(media.values()) == [emblem.EMBLEM_FILE.read_bytes()]
    assert all(name.endswith(".png") for name in media)
    first = body[0]
    assert first.tag == f"{{{W}}}p"
    assert first.find("w:pPr/w:jc", NS).get(f"{{{W}}}val") == "center"
    extent = first.find(".//wp:inline/wp:extent", NS)
    assert int(extent.get("cx")) == EMBLEM_WIDTH_EMU
    assert int(extent.get("cy")) == pytest.approx(EMBLEM_WIDTH_EMU * EMBLEM_RATIO, abs=1)
    assert len(body.findall(".//w:drawing", NS)) == 1


@pytest.mark.parametrize("kind", FIVE)
def test_every_pdf_has_the_emblem_centered_above_the_first_text_on_its_first_page_only(
    gen, five, kind
):
    with pymupdf.open(file_path(gen, five[kind], DocumentFormat.PDF)) as pdf:
        first = pdf[0]
        images = first.get_images(full=True)
        assert len(images) == 1
        (rect,) = first.get_image_rects(images[0][0])
        words = first.get_text("words")
        assert rect.width == pytest.approx(EMBLEM_WIDTH_PT, abs=0.5)
        assert rect.height == pytest.approx(EMBLEM_WIDTH_PT * EMBLEM_RATIO, abs=0.5)
        assert (rect.x0 + rect.x1) / 2 == pytest.approx(text_center(kind, first), abs=1)
        assert rect.y1 <= min(word[1] for word in words)
        assert all(page.get_images() == [] for page in list(pdf)[1:])
        if kind is DocumentKind.COMPROVANTE:
            assert len(pdf) > 1  # the cover has it and the table of contents and the rest do not


# --- the Parecer follows the model (PMOD-19, PMOD-20, PMOD-24) ----------------------------------


def test_the_parecer_has_the_paragraph_of_the_model_and_none_of_the_old_sections(gen, five):
    parecer = five[DocumentKind.PARECER]

    for fmt, text in flat_texts(gen, parecer).items():
        assert "reuniram-se os membros da Banca de Análise" in text, fmt
        assert "nomeados pela Portaria nº 77/2025" in text, fmt
        assert "Aos dois dias do mês de abril de dois mil e vinte e cinco" in text, fmt
        assert "os membros APROVARAM o referido relatório." in text, fmt
        for forbidden in ("Total geral", "Mínimo de referência", "Observações"):
            assert forbidden not in text, (fmt, forbidden)


def test_the_snapshot_of_the_parecer_has_the_total_of_the_tabela(gen, five):
    parecer, table = five[DocumentKind.PARECER], five[DocumentKind.TABELA]

    assert parecer.snapshot["total"] == table.snapshot["total"]
    assert parecer.snapshot["table_generation_id"] == str(table.id)


# --- no file without the emblem (BRAS-10) -------------------------------------------------------


@pytest.mark.parametrize("kind", FIVE)
def test_without_the_emblem_file_the_row_fails_with_the_fixed_message_and_leaves_no_file(
    gen, five, kind, monkeypatch, tmp_path, caplog
):
    before = stored_files(gen)
    monkeypatch.setattr(emblem, "EMBLEM_FILE", tmp_path / "private-dir" / "ufpa.png")
    requested = ask(gen, kind)

    with caplog.at_level(logging.DEBUG):
        run_one(gen)

    with gen.world.uow_factory() as uow:
        failed = uow.generations.get(requested.id)
    assert failed.state is GenerationState.FALHOU
    assert failed.error_code is GenerationCode.ERRO_INTERNO
    assert failed.error_message == FIXED_MESSAGE
    assert failed.version_number is None and failed.files == ()
    assert stored_files(gen) == before
    errors = [r.getMessage() for r in caplog.records if r.levelno >= logging.ERROR]
    assert errors == [
        f"generation_id={requested.id} kind={kind.value} error_type=EmblemUnavailable"
    ]
    assert str(tmp_path) not in caplog.text and "private-dir" not in caplog.text


# --- a version already generated never changes (BRAS-11, AD-012) --------------------------------


def digests(gen, generation) -> dict[DocumentFormat, str]:
    return {
        fmt: hashlib.sha256(file_path(gen, generation, fmt).read_bytes()).hexdigest()
        for fmt in DocumentFormat
    }


def test_version_1_keeps_its_bytes_after_version_2_of_the_parecer_and_of_the_tabela(gen, five):
    tabela_1, parecer_1 = five[DocumentKind.TABELA], five[DocumentKind.PARECER]
    before = {tabela_1.id: digests(gen, tabela_1), parecer_1.id: digests(gen, parecer_1)}

    tabela_2 = ready(gen, DocumentKind.TABELA)
    parecer_2 = ready(gen, DocumentKind.PARECER)

    assert (tabela_2.version_number, parecer_2.version_number) == (2, 2)
    assert digests(gen, tabela_1) == before[tabela_1.id]
    assert digests(gen, parecer_1) == before[parecer_1.id]
    assert digests(gen, parecer_2) != before[parecer_1.id]  # the new version is its own files


def test_a_new_version_is_made_with_the_emblem(gen, five):
    parecer_2 = ready(gen, DocumentKind.PARECER)

    body, media = docx_body(file_path(gen, parecer_2, DocumentFormat.DOCX))
    assert len(media) == 1 and len(body.findall(".//w:drawing", NS)) == 1
    with pymupdf.open(file_path(gen, parecer_2, DocumentFormat.PDF)) as pdf:
        assert len(pdf[0].get_images()) == 1


def test_a_failed_attempt_with_no_emblem_does_not_touch_the_version_that_exists(
    gen, five, monkeypatch, tmp_path
):
    parecer_1 = five[DocumentKind.PARECER]
    before = digests(gen, parecer_1)
    monkeypatch.setattr(emblem, "EMBLEM_FILE", tmp_path / "ufpa.png")
    ask(gen, DocumentKind.PARECER)

    run_one(gen)

    assert digests(gen, parecer_1) == before
    with gen.world.uow_factory() as uow:
        rows = uow.generations.list_for_process(gen.world.process.id, DocumentKind.PARECER)
    assert sorted(g.version_number for g in rows if g.state is GenerationState.PRONTO) == [1]

