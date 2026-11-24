"""NBASE-05: private storage of the PDF of a norm, in a temporary directory."""

import hashlib
import re
import stat
from pathlib import Path

import pytest

from app.domain.entities.norm import NormFile
from app.domain.repositories.ports import StagedNormFile
from app.infrastructure.storage.norm_storage import LocalNormStorage

CONTENT = b"%PDF-1.7 norma ficticia \x00\xff" * 50


@pytest.fixture
def storage(tmp_path):
    return LocalNormStorage(tmp_path / "storage")


@pytest.fixture
def staged(tmp_path):
    path = tmp_path / "staged.bin"
    path.write_bytes(CONTENT)
    return StagedNormFile(path=path, original_name="norma sintetica.pdf")


def mode_of(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


def test_saved_file_is_under_norms_with_a_random_pdf_name_and_opens_with_the_same_bytes(
    storage, staged, tmp_path
):
    stored = storage.save(staged)

    assert isinstance(stored, NormFile)
    assert re.fullmatch(r"[0-9a-f]{32}\.pdf", stored.internal_name)
    path = storage.open(stored.internal_name)
    assert path == tmp_path / "storage" / "norms" / stored.internal_name
    assert path.read_bytes() == CONTENT
    assert stored.original_name == "norma sintetica.pdf"


def test_the_stored_size_and_sha256_are_those_of_the_stored_bytes(storage, staged):
    stored = storage.save(staged)

    assert stored.size_bytes == len(CONTENT)
    assert stored.sha256 == hashlib.sha256(CONTENT).hexdigest()


def test_directory_is_0700_and_file_is_0600(storage, staged):
    stored = storage.save(staged)

    path = storage.open(stored.internal_name)
    assert mode_of(path) == 0o600
    assert mode_of(path.parent) == 0o700


def test_each_save_gets_a_distinct_name(storage, staged):
    names = {storage.save(staged).internal_name for _ in range(5)}

    assert len(names) == 5


@pytest.mark.parametrize(
    "name",
    [
        "../x.pdf",
        "../../etc/passwd",
        "a/b.pdf",
        "norma.pdf",
        f"{'a' * 32}.png",
        f"{'a' * 31}.pdf",
        f"{'A' * 32}.pdf",
        "",
    ],
)
def test_open_and_delete_refuse_a_name_outside_the_pattern(storage, name):
    with pytest.raises(ValueError):
        storage.open(name)
    with pytest.raises(ValueError):
        storage.delete(name)


def test_delete_removes_the_file(storage, staged):
    stored = storage.save(staged)
    path = storage.open(stored.internal_name)

    storage.delete(stored.internal_name)

    assert not path.exists()


def test_delete_of_a_missing_file_does_not_fail(storage):
    storage.delete("0" * 32 + ".pdf")
