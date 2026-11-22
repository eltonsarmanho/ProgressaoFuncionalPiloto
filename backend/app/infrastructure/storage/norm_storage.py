"""Private local storage of the PDF of a norm (NBASE-05).

Files live under `{root}/norms/{uuid4 hex}.pdf`. The name chosen by the user is never part of
a path. The directory is 0700 and the files 0600, and a stored file is never rewritten.
"""

import hashlib
import os
import re
from pathlib import Path
from uuid import uuid4

from app.domain.entities.norm import NormFile
from app.domain.repositories.ports import StagedNormFile

_INTERNAL_NAME = re.compile(r"^[0-9a-f]{32}\.pdf$")
_DIR_MODE = 0o700
_FILE_MODE = 0o600
_CHUNK = 1024 * 1024


class LocalNormStorage:
    def __init__(self, root: str | Path) -> None:
        self._dir = Path(root) / "norms"

    def _path(self, internal_name: str) -> Path:
        if not _INTERNAL_NAME.fullmatch(internal_name):
            raise ValueError("invalid internal name")
        return self._dir / internal_name

    def save(self, staged: StagedNormFile) -> NormFile:
        self._dir.mkdir(mode=_DIR_MODE, parents=True, exist_ok=True)
        self._dir.chmod(_DIR_MODE)
        internal_name = f"{uuid4().hex}.pdf"
        digest = hashlib.sha256()
        size = 0
        fd = os.open(self._dir / internal_name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, _FILE_MODE)
        with os.fdopen(fd, "wb") as out, staged.path.open("rb") as source:
            while chunk := source.read(_CHUNK):
                digest.update(chunk)
                size += len(chunk)
                out.write(chunk)
        return NormFile(internal_name, staged.original_name, size, digest.hexdigest())

    def open(self, internal_name: str) -> Path:
        return self._path(internal_name)

    def delete(self, internal_name: str) -> None:
        self._path(internal_name).unlink(missing_ok=True)
