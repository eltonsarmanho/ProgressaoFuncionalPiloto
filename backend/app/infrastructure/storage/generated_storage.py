"""Private storage of the generated documents (VER-01, VER-05, CMP-09).

Files live under `{root}/generated/{process_id}/{uuid4 hex}.{docx|pdf}`; the name never carries
the name of the professor. A writer writes to a `.tmp-*` path and `commit` renames it inside the
same directory, so the content is never read into memory (a Comprovante has up to 60 MB) and a
failed generation leaves no partial file under a final name. Directories are 0700, files 0600.
"""

import os
import re
import shutil
from collections.abc import Collection, Mapping
from pathlib import Path
from uuid import UUID, uuid4

_EXTENSIONS = frozenset({"docx", "pdf"})
_INTERNAL_NAME = re.compile(r"^[0-9a-f]{32}\.(?:docx|pdf)$")
_TEMP_PREFIX = ".tmp-"
_DIR_MODE = 0o700
_FILE_MODE = 0o600


class LocalGeneratedStorage:
    def __init__(self, root: str | Path) -> None:
        self._root = Path(root) / "generated"

    def _process_dir(self, process_id: UUID) -> Path:
        return self._root / str(process_id)

    def _ensure_private_dir(self, process_id: UUID) -> Path:
        directory = self._process_dir(process_id)
        directory.parent.parent.mkdir(mode=_DIR_MODE, parents=True, exist_ok=True)
        for path in (directory.parent, directory):
            path.mkdir(mode=_DIR_MODE, exist_ok=True)
            path.chmod(_DIR_MODE)
        return directory

    def new_temp_path(self, process_id: UUID) -> Path:
        """An empty `.tmp-*` file (0600) in the directory of the process, for a writer to fill."""
        path = self._ensure_private_dir(process_id) / f"{_TEMP_PREFIX}{uuid4().hex}"
        os.close(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, _FILE_MODE))
        return path

    def commit(self, process_id: UUID, temp: Path, extension: str) -> str:
        """Renames the temporary file to a random name and returns the internal name."""
        ext = extension.lower().lstrip(".")
        if ext not in _EXTENSIONS:
            raise ValueError(f"extension not allowed: {extension!r}")
        temp = Path(temp)
        if temp.parent != self._process_dir(process_id) or not temp.name.startswith(_TEMP_PREFIX):
            raise ValueError("not a temporary file of this process")
        internal_name = f"{uuid4().hex}.{ext}"
        temp.chmod(_FILE_MODE)
        os.replace(temp, temp.parent / internal_name)
        return internal_name

    def path(self, process_id: UUID, internal_name: str) -> Path:
        if not _INTERNAL_NAME.fullmatch(internal_name):
            raise ValueError("invalid internal name")
        return self._process_dir(process_id) / internal_name

    def delete(self, process_id: UUID, internal_name: str) -> None:
        """Removes the file; deleting a missing file is not an error."""
        self.path(process_id, internal_name).unlink(missing_ok=True)

    def free_bytes(self) -> int:
        """Free space of the volume that holds the files (ESPACO_INSUFICIENTE)."""
        probe = self._root
        while not probe.exists():
            probe = probe.parent
        return shutil.disk_usage(probe).free

    def cleanup(self, referenced: Mapping[UUID, Collection[str]]) -> int:
        """Removes every `.tmp-*` file and every stored file no row refers to; returns how many.

        `referenced` maps a process to the internal names that have a row. Meant for the start
        of the server, when no generation is writing; anything that is not a process directory
        or an internal name is left alone.
        """
        removed = 0
        if not self._root.is_dir():
            return 0
        for directory in self._root.iterdir():
            try:
                process_id = UUID(directory.name)
            except ValueError:
                continue
            if not directory.is_dir():
                continue
            keep = set(referenced.get(process_id, ()))
            for file in directory.iterdir():
                stale = file.name.startswith(_TEMP_PREFIX) or (
                    _INTERNAL_NAME.fullmatch(file.name) and file.name not in keep
                )
                if stale and file.is_file():
                    file.unlink(missing_ok=True)
                    removed += 1
        return removed
