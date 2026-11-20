"""DOC-05, DOC-06 and the file-name edge case: private storage with random names."""

import re
import stat
from pathlib import Path
from uuid import uuid4

import pytest

from app.infrastructure.storage.local_storage import LocalFileStorage, StoredFileNotFound

CONTENT = b"%PDF-1.7 conteudo ficticio \x00\xff"


@pytest.fixture
def storage(tmp_path):
    return LocalFileStorage(tmp_path / "storage")


def mode_of(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


def test_saved_path_is_uploads_process_uuid_and_extension(storage, tmp_path):
    process_id = uuid4()
    name = storage.save(process_id, ".pdf", CONTENT)
    assert re.fullmatch(r"[0-9a-f]{32}\.pdf", name)
    expected = tmp_path / "storage" / "uploads" / str(process_id) / name
    assert storage.path(process_id, name) == expected
    assert expected.is_file()


def test_write_then_read_returns_same_bytes(storage):
    process_id = uuid4()
    name = storage.save(process_id, ".pdf", CONTENT)
    with storage.open(process_id, name) as handle:
        assert handle.read() == CONTENT


def test_file_mode_is_0600(storage):
    process_id = uuid4()
    name = storage.save(process_id, ".png", CONTENT)
    assert mode_of(storage.path(process_id, name)) == 0o600


def test_directories_are_0700(storage):
    process_id = uuid4()
    name = storage.save(process_id, ".png", CONTENT)
    process_dir = storage.path(process_id, name).parent
    assert mode_of(process_dir) == 0o700
    assert mode_of(process_dir.parent) == 0o700


def test_each_save_gets_a_distinct_random_name(storage):
    process_id = uuid4()
    names = {storage.save(process_id, ".pdf", CONTENT) for _ in range(5)}
    assert len(names) == 5


@pytest.mark.parametrize("extension", [".pdf", ".jpg", ".jpeg", ".png", ".PDF", "png"])
def test_allowed_extensions_are_kept_lowercase(storage, extension):
    name = storage.save(uuid4(), extension, CONTENT)
    assert name.endswith("." + extension.lower().lstrip("."))


@pytest.mark.parametrize("extension", [".exe", ".docx", "", "../x.pdf", ".pdf/../../x", ".pdf\x00"])
def test_extension_outside_the_whitelist_is_refused(storage, extension):
    with pytest.raises(ValueError):
        storage.save(uuid4(), extension, CONTENT)


def test_path_never_contains_the_original_name(storage, tmp_path):
    """The API takes no file name, so a hostile name can never reach the disk path."""
    process_id = uuid4()
    hostile = "../../etc/passwd.pdf"
    name = storage.save(process_id, ".pdf", CONTENT)
    stored = storage.path(process_id, name)
    assert "passwd" not in str(stored)
    assert ".." not in stored.relative_to(tmp_path).parts
    assert hostile not in str(stored)
    assert not (tmp_path / "etc").exists()


@pytest.mark.parametrize("bad", ["../x.pdf", "a/b.pdf", "x.pdf", "", "/etc/passwd"])
def test_reading_with_a_forged_internal_name_is_refused(storage, bad):
    with pytest.raises(ValueError):
        storage.open(uuid4(), bad)
    with pytest.raises(ValueError):
        storage.delete(uuid4(), bad)


def test_delete_removes_the_file(storage):
    process_id = uuid4()
    name = storage.save(process_id, ".pdf", CONTENT)
    storage.delete(process_id, name)
    assert not storage.path(process_id, name).exists()


def test_delete_is_idempotent(storage):
    process_id = uuid4()
    name = storage.save(process_id, ".pdf", CONTENT)
    storage.delete(process_id, name)
    storage.delete(process_id, name)
    storage.delete(uuid4(), "0" * 32 + ".pdf")


def test_open_of_a_missing_file_raises_a_clear_error(storage):
    with pytest.raises(StoredFileNotFound, match="stored file not found"):
        storage.open(uuid4(), "0" * 32 + ".pdf")


def test_other_processes_directory_is_separate(storage):
    first, second = uuid4(), uuid4()
    name = storage.save(first, ".pdf", CONTENT)
    with pytest.raises(StoredFileNotFound):
        storage.open(second, name)
