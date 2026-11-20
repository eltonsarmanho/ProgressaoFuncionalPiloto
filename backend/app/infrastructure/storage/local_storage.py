"""Private local file storage (DOC-05, DOC-06).

Files live under `{root}/uploads/{process_id}/{uuid4}{ext}`. The name chosen by the user is
never part of a path; only the whitelisted extension survives. Directories are 0700 and files
0600, and a stored file is never rewritten.
"""

import os
import re
from pathlib import Path
from typing import BinaryIO
from uuid import UUID, uuid4

ALLOWED_EXTENSIONS = frozenset({".pdf", ".jpg", ".jpeg", ".png"})
_INTERNAL_NAME = re.compile(r"^[0-9a-f]{32}(?:\.(?:pdf|jpg|jpeg|png))$")
_DIR_MODE = 0o700
_FILE_MODE = 0o600


class StoredFileNotFound(FileNotFoundError):
    """The stored file does not exist (never stored, or already deleted)."""


class LocalFileStorage:
    def __init__(self, root: str | Path) -> None:
        self._root = Path(root)

    def _process_dir(self, process_id: UUID) -> Path:
        return self._root / "uploads" / str(process_id)

    def _ensure_private_dir(self, path: Path) -> None:
        path.mkdir(mode=_DIR_MODE, parents=True, exist_ok=True)
        path.chmod(_DIR_MODE)

    def save(self, process_id: UUID, extension: str, content: bytes) -> str:
        """Stores the bytes under a random name and returns the internal name."""
        ext = extension.lower()
        ext = ext if ext.startswith(".") else "." + ext
        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError(f"extension not allowed: {extension!r}")
        directory = self._process_dir(process_id)
        self._ensure_private_dir(directory.parent)
        self._ensure_private_dir(directory)
        internal_name = f"{uuid4().hex}{ext}"
        fd = os.open(directory / internal_name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, _FILE_MODE)
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
        return internal_name

    def path(self, process_id: UUID, internal_name: str) -> Path:
        if not _INTERNAL_NAME.fullmatch(internal_name):
            raise ValueError("invalid internal name")
        return self._process_dir(process_id) / internal_name

    def open(self, process_id: UUID, internal_name: str) -> BinaryIO:
        path = self.path(process_id, internal_name)
        try:
            return path.open("rb")
        except FileNotFoundError:
            raise StoredFileNotFound(f"stored file not found: {internal_name}") from None

    def delete(self, process_id: UUID, internal_name: str) -> None:
        """Removes the file; deleting a missing file is not an error."""
        self.path(process_id, internal_name).unlink(missing_ok=True)
