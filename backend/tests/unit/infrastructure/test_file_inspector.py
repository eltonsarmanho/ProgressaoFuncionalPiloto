"""DOC-02, DOC-04: the inspector reports the facts the upload rules decide on."""

import hashlib
from decimal import Decimal

import pymupdf
import pytest

from app.domain.rules.upload_validation import FileKind, UploadLimits, validate_upload
from app.infrastructure.files.inspector import PillowFileInspector
from tests.support import synthetic_docs as docs


@pytest.fixture
def inspect(tmp_path):
    inspector = PillowFileInspector()

    def run(data: bytes, name: str = "arquivo.bin"):
        path = tmp_path / name
        path.write_bytes(data)
        return inspector.inspect(path)

    return run


def test_plain_pdf_facts(inspect):
    facts = inspect(docs.pdf_with_text(["pagina um", "pagina dois", "pagina tres"]))
    assert facts.kind is FileKind.PDF
    assert facts.page_count == 3
    assert facts.has_active_content is False
    assert facts.is_encrypted is False
    assert facts.is_readable is True
    assert facts.megapixels is None


def test_size_is_the_file_size(inspect):
    data = docs.pdf_with_text()
    assert inspect(data).size_bytes == len(data)


def test_pdf_with_javascript_has_active_content(inspect):
    facts = inspect(docs.pdf_with_javascript())
    assert facts.has_active_content is True
    assert facts.is_readable is True


def test_pdf_with_javascript_inside_an_object_stream_is_found(inspect):
    doc = pymupdf.open()
    doc.new_page()
    doc.xref_set_key(
        doc.pdf_catalog(), "OpenAction", "<< /S /JavaScript /JS (app.alert\\('x'\\);) >>"
    )
    facts = inspect(doc.tobytes(use_objstms=True, garbage=2))
    assert facts.has_active_content is True


def test_pdf_with_launch_link_has_active_content(inspect):
    doc = pymupdf.open()
    page = doc.new_page()
    link = {"kind": pymupdf.LINK_LAUNCH, "from": pymupdf.Rect(10, 10, 80, 40), "file": "x"}
    page.insert_link(link)
    facts = inspect(doc.tobytes())
    assert facts.has_active_content is True


def test_pdf_with_embedded_file_has_active_content(inspect):
    assert inspect(docs.pdf_with_embedded_file()).has_active_content is True


def test_encrypted_pdf_is_reported_encrypted(inspect):
    facts = inspect(docs.pdf_encrypted())
    assert facts.is_encrypted is True
    assert facts.kind is FileKind.PDF


def test_corrupt_pdf_is_unreadable_without_raising(inspect):
    facts = inspect(b"%PDF-1.4\nisto nao e um pdf de verdade\n%%EOF")
    assert facts.kind is FileKind.PDF
    assert facts.is_readable is False
    assert facts.has_active_content is False


def test_truncated_pdf_is_unreadable_without_raising(inspect):
    data = docs.pdf_with_text()
    facts = inspect(data[: len(data) // 3])
    assert facts.is_readable is False


def test_empty_file_is_unknown_and_unreadable(inspect):
    facts = inspect(b"")
    assert facts.kind is FileKind.UNKNOWN
    assert facts.is_readable is False


def test_unknown_signature_is_unknown_kind(inspect):
    assert inspect(b"MZ\x90\x00 executavel").kind is FileKind.UNKNOWN


def test_png_facts_with_megapixels(inspect):
    facts = inspect(docs.png_with_text())
    assert facts.kind is FileKind.PNG
    assert facts.megapixels == Decimal(2480 * 3508) / Decimal(1_000_000)
    assert facts.page_count is None
    assert facts.is_readable is True
    assert facts.has_active_content is False


def test_jpeg_facts_with_megapixels(inspect):
    facts = inspect(docs.jpg_with_text())
    assert facts.kind is FileKind.JPEG
    assert facts.megapixels == Decimal(2480 * 3508) / Decimal(1_000_000)
    assert facts.is_readable is True


def test_image_above_100_megapixels_is_reported_above_the_limit(inspect):
    facts = inspect(docs.png_huge())
    assert facts.megapixels is not None and facts.megapixels > 100
    assert facts.is_readable is True


def test_decompression_bomb_is_reported_above_100_megapixels(inspect, monkeypatch):
    from PIL import Image

    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 1_000_000)  # error above 2 x this
    facts = inspect(docs.png_huge())
    assert facts.megapixels is not None and facts.megapixels > 100
    assert facts.is_readable is True


def test_truncated_png_is_unreadable(inspect):
    data = docs.png_with_text()
    assert inspect(data[: len(data) // 2]).is_readable is False


def test_truncated_jpeg_is_unreadable(inspect):
    data = docs.jpg_with_text()
    assert inspect(data[: len(data) // 2]).is_readable is False


def test_inspection_never_modifies_the_file(tmp_path):
    path = tmp_path / "doc.pdf"
    path.write_bytes(docs.pdf_with_javascript())
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    PillowFileInspector().inspect(path)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before


@pytest.mark.parametrize(
    ("make", "ext", "codes"),
    [
        (docs.pdf_with_text, ".pdf", []),
        (docs.jpg_with_text, ".jpg", []),
        (docs.png_with_text, ".png", []),
        (docs.pdf_with_javascript, ".pdf", ["ARQUIVO_INVALIDO"]),
        (docs.pdf_encrypted, ".pdf", ["ARQUIVO_INVALIDO"]),
        (docs.png_huge, ".png", ["IMAGEM_GRANDE"]),
    ],
)
def test_facts_feed_the_upload_rules(inspect, make, ext, codes):
    rejections = validate_upload(inspect(make()), None, ext, UploadLimits())
    assert [r.code for r in rejections] == codes
