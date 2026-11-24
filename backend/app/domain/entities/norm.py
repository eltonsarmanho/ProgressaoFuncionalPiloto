"""Norm entity and its citation in alerts (NBASE-01, NBASE-08, NLINK-06)."""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from uuid import UUID


class NormKind(StrEnum):
    LEI = "LEI"
    RESOLUCAO = "RESOLUCAO"
    INSTRUCAO_NORMATIVA = "INSTRUCAO_NORMATIVA"
    MANUAL = "MANUAL"
    TABELA = "TABELA"
    OUTRO = "OUTRO"


@dataclass(frozen=True)
class NormFile:
    internal_name: str
    original_name: str
    size_bytes: int
    sha256: str


@dataclass(frozen=True)
class NormCitation:
    """What an alert shows about the norm behind its rule."""

    id: UUID
    code: str
    title: str
    source_url: str | None
    has_file: bool
    archived: bool


@dataclass
class Norm:
    id: UUID
    code: str
    title: str
    kind: NormKind
    issuer: str
    published_on: date
    valid_from: date | None = None
    valid_to: date | None = None
    source_url: str | None = None
    file: NormFile | None = None
    notes: str | None = None
    archived: bool = False
    version: int = 1

    def citation(self) -> NormCitation:
        return NormCitation(
            id=self.id,
            code=self.code,
            title=self.title,
            source_url=self.source_url,
            has_file=self.file is not None,
            archived=self.archived,
        )
