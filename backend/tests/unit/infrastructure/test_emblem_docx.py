"""BRAS-06, BRAS-07, BRAS-10: the emblem paragraph of the DOCX documents, centered, 20 mm wide, with
the height in proportion and 3 mm of space below, and a failure when the file is not there."""

import zipfile

import pytest
from docx import Document
from lxml import etree

from app.infrastructure.documents import emblem
from app.infrastructure.documents.docx_support import add_emblem
from app.infrastructure.documents.emblem import EMBLEM_FILE, EmblemUnavailable

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
WP = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
NS = {"w": W, "wp": WP, "a": A}
WIDTH_EMU = 720_000  # 20 mm
SPACE_TWIPS = 170  # 3 mm = 170.08 twips, rounded to a twentieth of a point by Word


def saved(tmp_path, document) -> str:
    target = tmp_path / "brasao.docx"
    document.save(target)
    return str(target)


def body_of(path):
    with zipfile.ZipFile(path) as archive:
        return etree.fromstring(archive.read("word/document.xml")).find("w:body", NS)


def test_the_first_element_of_the_body_is_a_centered_paragraph_with_an_inline_picture(tmp_path):
    document = Document()
    add_emblem(document)
    body = body_of(saved(tmp_path, document))
    first = body[0]
    assert first.tag == f"{{{W}}}p"
    assert len(first.findall(".//w:drawing/wp:inline", NS)) == 1
    assert first.find("w:pPr/w:jc", NS).get(f"{{{W}}}val") == "center"


def test_the_emblem_comes_before_anything_added_after_it(tmp_path):
    document = Document()
    add_emblem(document)
    document.add_paragraph("Primeira linha")
    body = body_of(saved(tmp_path, document))
    assert body[0].findall(".//w:drawing", NS)
    assert not body[1].findall(".//w:drawing", NS)


def test_the_picture_is_20_mm_wide_and_keeps_the_proportion_of_279_by_351(tmp_path):
    document = Document()
    add_emblem(document)
    extent = body_of(saved(tmp_path, document)).find(".//wp:inline/wp:extent", NS)
    width, height = int(extent.get("cx")), int(extent.get("cy"))
    assert width == WIDTH_EMU
    assert abs(height - width * 351 / 279) <= 1


def test_the_space_after_the_paragraph_is_3_mm_and_it_stays_with_the_next(tmp_path):
    document = Document()
    add_emblem(document)
    properties = body_of(saved(tmp_path, document))[0].find("w:pPr", NS)
    assert abs(int(properties.find("w:spacing", NS).get(f"{{{W}}}after")) - SPACE_TWIPS) <= 1
    keep_next = properties.find("w:keepNext", NS)
    assert keep_next is not None
    # a bare <w:keepNext/> is on; an explicit val of 0 or false would turn it off
    assert keep_next.get(f"{{{W}}}val") in (None, "1", "true", "on")


def test_the_alternative_text_is_the_name_of_the_emblem(tmp_path):
    document = Document()
    add_emblem(document)
    properties = body_of(saved(tmp_path, document)).find(".//wp:inline/wp:docPr", NS)
    assert properties.get("descr") == "Brasão da Universidade Federal do Pará"


def test_the_package_has_one_png_equal_to_the_packaged_file(tmp_path):
    document = Document()
    add_emblem(document)
    with zipfile.ZipFile(saved(tmp_path, document)) as archive:
        media = [name for name in archive.namelist() if name.startswith("word/media/")]
        assert len(media) == 1
        assert media[0].endswith(".png")
        assert archive.read(media[0]) == EMBLEM_FILE.read_bytes()


def test_without_the_file_it_fails_and_nothing_is_written_to_the_document(monkeypatch, tmp_path):
    monkeypatch.setattr(emblem, "EMBLEM_FILE", tmp_path / "ufpa.png")
    document = Document()
    with pytest.raises(EmblemUnavailable, match="ufpa.png"):
        add_emblem(document)
    assert len(document.paragraphs) == 0
    assert len(document.inline_shapes) == 0
