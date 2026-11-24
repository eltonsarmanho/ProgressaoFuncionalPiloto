"""VER-01, VER-05, CMP-09: private storage of the generated files, written to a temporary path
and renamed (never loaded into memory)."""

import os
import re
import stat
from pathlib import Path
from uuid import uuid4

import pytest

from app.infrastructure.storage.generated_storage import LocalGeneratedStorage

NAME = re.compile(r"^[0-9a-f]{32}\.(docx|pdf)$")


@pytest.fixture
def storage(tmp_path):
    return LocalGeneratedStorage(tmp_path / "storage")


def mode_of(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


def write_and_commit(storage, process_id, extension="pdf", content=b"%PDF-1.7 ficticio"):
    temp = storage.new_temp_path(process_id)
    temp.write_bytes(content)
    return temp, storage.commit(process_id, temp, extension)


def test_committed_file_lives_in_generated_process_dir_with_permissions_0700_and_0600(
    storage, tmp_path
):
    process_id = uuid4()
    _, name = write_and_commit(storage, process_id)

    path = storage.path(process_id, name)

    assert path == tmp_path / "storage" / "generated" / str(process_id) / name
    assert path.is_file()
    assert mode_of(path) == 0o600
    assert mode_of(path.parent) == 0o700
    assert mode_of(path.parent.parent) == 0o700


@pytest.mark.parametrize("extension", ["docx", "pdf", ".docx", ".PDF"])
def test_internal_name_is_random_hex_with_the_extension_and_no_other_text(storage, extension):
    process_id = uuid4()
    _, name = write_and_commit(storage, process_id, extension)

    assert NAME.fullmatch(name)
    assert name.endswith(extension.lower().lstrip("."))


def test_each_commit_gets_a_distinct_name(storage):
    process_id = uuid4()
    names = {write_and_commit(storage, process_id)[1] for _ in range(5)}
    assert len(names) == 5


def test_temp_path_is_a_tmp_file_inside_the_directory_of_the_process_with_mode_0600(storage):
    process_id = uuid4()
    temp = storage.new_temp_path(process_id)

    assert temp.name.startswith(".tmp-")
    assert temp.parent == storage.path(process_id, "0" * 32 + ".pdf").parent
    assert mode_of(temp) == 0o600
    assert mode_of(temp.parent) == 0o700
    assert storage.new_temp_path(process_id) != temp


def test_commit_renames_in_place_without_copying_the_content(storage):
    process_id = uuid4()
    temp = storage.new_temp_path(process_id)
    temp.write_bytes(b"x" * 2_000_000)
    inode = temp.stat().st_ino

    name = storage.commit(process_id, temp, "pdf")

    final = storage.path(process_id, name)
    assert final.stat().st_ino == inode
    assert final.stat().st_size == 2_000_000
    assert not temp.exists()


def test_commit_gives_0600_even_when_the_writer_left_another_mode(storage):
    process_id = uuid4()
    temp = storage.new_temp_path(process_id)
    temp.write_bytes(b"conteudo")
    temp.chmod(0o644)

    name = storage.commit(process_id, temp, "docx")

    assert mode_of(storage.path(process_id, name)) == 0o600


def test_commit_refuses_an_extension_that_is_not_docx_or_pdf(storage):
    process_id = uuid4()
    temp = storage.new_temp_path(process_id)
    with pytest.raises(ValueError):
        storage.commit(process_id, temp, "exe")
    assert temp.exists()


def test_commit_refuses_a_file_that_is_not_a_temp_of_the_process(storage, tmp_path):
    process_id = uuid4()
    storage.new_temp_path(process_id)
    stranger = tmp_path / "fora.pdf"
    stranger.write_bytes(b"x")
    with pytest.raises(ValueError):
        storage.commit(process_id, stranger, "pdf")
    with pytest.raises(ValueError):
        storage.commit(uuid4(), storage.new_temp_path(process_id), "pdf")
    assert stranger.exists()


@pytest.mark.parametrize("name", ["../x.pdf", "abc.pdf", "0" * 32 + ".exe", "0" * 32 + "/a.pdf"])
def test_path_refuses_names_that_are_not_internal_names(storage, name):
    with pytest.raises(ValueError):
        storage.path(uuid4(), name)


def test_delete_removes_the_file_and_a_missing_file_is_not_an_error(storage):
    process_id = uuid4()
    _, name = write_and_commit(storage, process_id)

    storage.delete(process_id, name)
    storage.delete(process_id, name)

    assert not storage.path(process_id, name).exists()


def test_cleanup_removes_temp_files_and_files_without_a_row_and_keeps_the_referenced(storage):
    process_id = uuid4()
    other = uuid4()
    _, kept = write_and_commit(storage, process_id)
    _, orphan = write_and_commit(storage, process_id, "docx")
    _, other_orphan = write_and_commit(storage, other)
    leftover = storage.new_temp_path(process_id)
    leftover.write_bytes(b"parcial")

    removed = storage.cleanup({process_id: {kept}})

    assert removed == 3
    assert storage.path(process_id, kept).exists()
    assert not storage.path(process_id, orphan).exists()
    assert not storage.path(other, other_orphan).exists()
    assert not leftover.exists()


def test_cleanup_leaves_alone_what_is_not_a_process_directory_or_a_stored_name(storage, tmp_path):
    root = tmp_path / "storage" / "generated"
    process_id = uuid4()
    _, kept = write_and_commit(storage, process_id)
    (root / "nao-e-uuid").mkdir()
    (root / "nao-e-uuid" / "a.pdf").write_bytes(b"x")
    (root / str(process_id) / "notas.txt").write_bytes(b"x")

    removed = storage.cleanup({process_id: {kept}})

    assert removed == 0
    assert (root / "nao-e-uuid" / "a.pdf").exists()
    assert (root / str(process_id) / "notas.txt").exists()


def test_cleanup_on_an_empty_storage_removes_nothing(storage):
    assert storage.cleanup({}) == 0


def test_free_bytes_is_the_free_space_of_the_volume_even_before_the_first_file(storage, tmp_path):
    expected = os.statvfs(tmp_path).f_bavail * os.statvfs(tmp_path).f_frsize
    free = storage.free_bytes()
    assert free > 0
    assert abs(free - expected) < 50_000_000


def test_remove_process_dir_removes_the_empty_directory_only(storage, tmp_path):
    process_id = uuid4()
    _, name = write_and_commit(storage, process_id)
    directory = tmp_path / "storage" / "generated" / str(process_id)

    assert storage.remove_process_dir(process_id) is False
    assert (directory / name).is_file()

    storage.delete(process_id, name)
    assert storage.remove_process_dir(process_id) is True
    assert not directory.exists()
    assert (tmp_path / "storage" / "generated").is_dir()


def test_remove_process_dir_of_a_missing_directory_is_not_an_error(storage):
    assert storage.remove_process_dir(uuid4()) is False


def test_remove_process_dir_never_removes_a_foreign_file(storage, tmp_path):
    process_id = uuid4()
    _, name = write_and_commit(storage, process_id)
    directory = tmp_path / "storage" / "generated" / str(process_id)
    storage.delete(process_id, name)
    (directory / "outro.txt").write_text("alheio")

    assert storage.remove_process_dir(process_id) is False
    assert (directory / "outro.txt").read_text() == "alheio"
