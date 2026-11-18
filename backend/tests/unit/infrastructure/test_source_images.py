"""CMP-08, CMP-12, CMP-13: images and rasterized pages as original pages of the Comprovante."""

import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import pymupdf
import pytest

from app.domain.entities.generated import GenerationAlertCode, GenerationCode
from app.domain.rules.comprovante_plan import ComprovanteRefused
from app.infrastructure.documents.source_pages import STRIP_HEIGHT, attach, attach_image
from tests.support.pdf_pages import (
    render,
    reopened,
    source_pdf,
    write_image,
    write_png_header_only,
)

BACKEND = Path(__file__).resolve().parents[3]


def sheet_size(page: pymupdf.Page) -> tuple[float, float]:
    return round(page.rect.width, 1), round(page.rect.height - STRIP_HEIGHT, 1)


def attached_image(path: Path, number: int = 4, **kwargs) -> pymupdf.Document:
    out = pymupdf.open()
    attach_image(out, path, number, **kwargs)
    return reopened(out)


def test_a_jpeg_becomes_a_page_of_its_size_in_points_at_its_dpi(tmp_path):
    path = tmp_path / "foto.jpg"
    write_image(path, "JPEG", (1500, 2100), dpi=300)

    out = attached_image(path)

    assert sheet_size(out[0]) == (360.0, 504.0)


def test_an_image_without_dpi_is_taken_as_150_dpi(tmp_path):
    jpeg, png = tmp_path / "a.jpg", tmp_path / "b.png"
    write_image(jpeg, "JPEG", (1500, 2100))
    write_image(png, "PNG", (1500, 2100))

    assert sheet_size(attached_image(jpeg)[0]) == (720.0, 1008.0)
    assert sheet_size(attached_image(png)[0]) == (720.0, 1008.0)


def test_a_huge_page_is_scaled_down_to_14400_points_on_the_longest_side(tmp_path):
    path = tmp_path / "faixa.png"
    write_image(path, "PNG", (36000, 100), mode="1")

    out = attached_image(path)

    assert sheet_size(out[0]) == (14400.0, 40.0)


def test_the_jpeg_is_embedded_with_its_own_bytes_and_the_strip_has_the_number(tmp_path):
    path = tmp_path / "foto.jpg"
    original = write_image(path, "JPEG", (600, 800), dpi=150)

    out = attached_image(path, number=9)

    image = out.extract_image(out[0].get_images(full=True)[0][0])
    assert (image["ext"], image["image"]) == ("jpeg", original)
    area = pymupdf.Rect(0, out[0].rect.height - STRIP_HEIGHT, out[0].rect.width, out[0].rect.height)
    assert out[0].get_text(clip=area).strip() == "Comprovante p. 9"


def test_a_png_of_12_megapixels_enters_and_one_more_pixel_is_refused_before_decoding(tmp_path):
    fits = tmp_path / "doze.png"
    write_image(fits, "PNG", (4000, 3000), mode="L")
    over = tmp_path / "doze_mais_um.png"
    write_png_header_only(over, (4001, 3000))  # cannot be decoded, only measured
    document_id = uuid4()

    assert len(attached_image(fits)) == 1
    with pytest.raises(ComprovanteRefused) as refused:
        attached_image(over, document_id=document_id)

    assert refused.value.code is GenerationCode.IMAGEM_GRANDE_DEMAIS
    assert refused.value.document_id == document_id


def test_a_jpeg_of_40_megapixels_enters_without_being_decoded(tmp_path):
    path = tmp_path / "grande.jpg"
    write_image(path, "JPEG", (8000, 5000), dpi=300)
    script = (
        "import resource, pymupdf\n"
        "from app.infrastructure.documents.source_pages import attach_image\n"
        "out = pymupdf.open()\n"
        "before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss\n"
        f"attach_image(out, {str(path)!r}, 3)\n"
        "after = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss\n"
        "print((after - before) // 1024, len(out))\n"
    )

    done = subprocess.run(
        [sys.executable, "-c", script], cwd=BACKEND, capture_output=True, text=True, check=True
    )

    growth_mb, pages = map(int, done.stdout.split())
    assert pages == 1
    assert growth_mb < 40  # decoding 40 megapixels would take about 120 MB


def cropped_and_rotated(rotation: int = 90) -> pymupdf.Document:
    doc = source_pdf(pages=1)
    doc[0].set_cropbox(pymupdf.Rect(40, 60, 500, 700))
    doc[0].set_rotation(rotation)
    return reopened(doc)


def test_a_rotated_page_with_a_smaller_crop_is_rasterized_at_200_dpi_with_an_alert():
    src = cropped_and_rotated()
    out = pymupdf.open()

    alert = attach(out, src, 0, 6, document_name="certificado.pdf")
    out = reopened(out)

    assert alert is not None
    assert alert.code is GenerationAlertCode.PAGINA_RASTERIZADA
    assert "certificado.pdf" in alert.message and "página 1" in alert.message
    assert sheet_size(out[0]) == (round(src[0].rect.width, 1), round(src[0].rect.height, 1))
    image = out.extract_image(out[0].get_images(full=True)[0][0])
    assert image["ext"] == "jpeg"
    assert image["width"] == round(src[0].rect.width * 200 / 72)


def test_the_rasterized_page_keeps_what_is_visible():
    src = cropped_and_rotated()
    out = pymupdf.open()
    attach(out, src, 0, 6)
    out = reopened(out)
    zoom = 200 / 72
    area = pymupdf.Rect(0, 0, out[0].rect.width, out[0].rect.height - STRIP_HEIGHT)

    drawn, seen = render(out[0], clip=area, zoom=zoom), render(src[0], zoom=zoom)

    assert len(drawn) == len(seen)
    mean_gap = sum(abs(a - b) for a, b in zip(drawn, seen, strict=True)) / len(seen)
    assert mean_gap < 4  # JPEG 92 noise only; a lost or shifted picture is far above this


def test_a_rotated_page_without_a_crop_and_a_crop_without_rotation_stay_vector():
    rotated = source_pdf(pages=1)
    rotated[0].set_rotation(90)
    cropped = source_pdf(pages=1)
    cropped[0].set_cropbox(pymupdf.Rect(20, 20, 560, 800))

    for doc in (reopened(rotated), reopened(cropped)):
        out = pymupdf.open()
        assert attach(out, doc, 0, 2) is None
        assert "Origem pagina 1" in reopened(out)[0].get_text()


def test_a_pdf_page_of_52_megapixels_is_attached_without_rasterizing_or_failing(tmp_path):
    jpeg = tmp_path / "gigante.jpg"
    write_image(jpeg, "JPEG", (9000, 5800), dpi=300)
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    page.insert_image(pymupdf.Rect(0, 0, 595, 842), filename=str(jpeg))
    src = reopened(doc)
    out = pymupdf.open()

    alert = attach(out, src, 0, 2)

    assert alert is None
    assert len(out) == 1
    assert len(out[0].get_images(full=True)) == 1  # still the picture, not a new rasterization
