"""BRAS-06, BRAS-09, BRAS-10: the emblem of the UFPA is a PNG versioned inside the package, with the
size of the spec, and a missing or invalid file fails with a clear error."""

from pathlib import Path

import pytest
from PIL import Image

import app
from app.infrastructure.documents import emblem
from app.infrastructure.documents.emblem import (
    EmblemUnavailable,
    emblem_path,
    emblem_size_mm,
)

BACKEND = Path(app.__file__).resolve().parent.parent


def test_the_packaged_file_is_inside_the_app_folder_the_dockerfile_copies():
    path = emblem_path()
    assert path.name == "ufpa.png"
    assert path.is_file()
    assert path.resolve().is_relative_to(Path(app.__file__).resolve().parent)
    assert "COPY app ./app" in (BACKEND / "Dockerfile").read_text()


def test_the_packaged_file_is_a_valid_png_of_279_by_351_pixels():
    path = emblem_path()
    assert path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    with Image.open(path) as image:
        image.load()
        assert image.format == "PNG"
        assert image.size == (279, 351)


def test_the_size_is_20_mm_wide_and_proportional_in_height():
    width, height = emblem_size_mm()
    assert width == 20.0
    assert height == pytest.approx(20 * 351 / 279, abs=0.001)
    assert height == pytest.approx(25.16, abs=0.01)


def test_the_constants_are_20_mm_of_width_and_3_mm_of_gap():
    assert emblem.EMBLEM_WIDTH_MM == 20.0
    assert emblem.EMBLEM_GAP_MM == 3.0


def test_a_missing_file_fails_naming_the_file_and_not_the_server_path(monkeypatch, tmp_path):
    secret_dir = tmp_path / "pasta-do-servidor"
    monkeypatch.setattr(emblem, "EMBLEM_FILE", secret_dir / "ufpa.png")
    for call in (emblem_path, emblem_size_mm):
        with pytest.raises(EmblemUnavailable) as raised:
            call()
        assert "ufpa.png" in str(raised.value)
        assert "pasta-do-servidor" not in str(raised.value)
        assert str(tmp_path) not in str(raised.value)


def test_an_empty_file_fails(monkeypatch, tmp_path):
    empty = tmp_path / "ufpa.png"
    empty.write_bytes(b"")
    monkeypatch.setattr(emblem, "EMBLEM_FILE", empty)
    for call in (emblem_path, emblem_size_mm):
        with pytest.raises(EmblemUnavailable, match="ufpa.png"):
            call()


def test_a_text_file_fails(monkeypatch, tmp_path):
    text = tmp_path / "ufpa.png"
    text.write_text("isto não é um PNG, mas tem o nome certo")
    monkeypatch.setattr(emblem, "EMBLEM_FILE", text)
    for call in (emblem_path, emblem_size_mm):
        with pytest.raises(EmblemUnavailable, match="ufpa.png"):
            call()


def test_the_error_is_a_runtime_error_so_the_generation_closes_as_failed():
    assert issubclass(EmblemUnavailable, RuntimeError)


def test_the_emblem_does_not_depend_on_the_img_folder_of_the_backend():
    dockerfile = (BACKEND / "Dockerfile").read_text()
    assert not any(line.startswith("COPY img") for line in dockerfile.splitlines())
    for source in (BACKEND / "app").rglob("*.py"):
        assert "img/ufpa.png" not in source.read_text(), source
