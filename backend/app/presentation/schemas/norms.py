"""Norm schemas (NBASE-01..10, NLIST-01, NLINK-06)."""

from datetime import date
from uuid import UUID

from pydantic import BaseModel

from app.application.use_cases.norms import LinkedRule, NormFields, NormWithLinks
from app.domain.entities.norm import NormKind


def file_url(norm_id: UUID) -> str:
    return f"/api/norms/{norm_id}/file"


class NormIn(BaseModel):
    code: str
    title: str
    kind: NormKind
    issuer: str
    published_on: date
    valid_from: date | None = None
    valid_to: date | None = None
    source_url: str | None = None
    notes: str | None = None

    def fields(self) -> NormFields:
        return NormFields(**self.model_dump(exclude={"code"}))


class NormUpdate(BaseModel):
    """The code is not editable: a `code` sent in the body is ignored."""

    title: str
    kind: NormKind
    issuer: str
    published_on: date
    valid_from: date | None = None
    valid_to: date | None = None
    source_url: str | None = None
    notes: str | None = None
    expected_version: int

    def fields(self) -> NormFields:
        return NormFields(**self.model_dump(exclude={"expected_version"}))


class VersionIn(BaseModel):
    expected_version: int


class NormFileOut(BaseModel):
    original_name: str
    size_bytes: int
    url: str


class LinkedRuleOut(BaseModel):
    kind: str
    name: str
    detail: str | None

    @classmethod
    def of(cls, rule: LinkedRule) -> "LinkedRuleOut":
        return cls(kind=rule.kind, name=rule.name, detail=rule.detail)


class NormOut(BaseModel):
    id: UUID
    code: str
    title: str
    kind: NormKind
    issuer: str
    published_on: date
    valid_from: date | None
    valid_to: date | None
    source_url: str | None
    notes: str | None
    archived: bool
    version: int
    file: NormFileOut | None
    linked_rules: list[LinkedRuleOut]

    @classmethod
    def of(cls, found: NormWithLinks) -> "NormOut":
        n = found.norm
        return cls(
            id=n.id,
            code=n.code,
            title=n.title,
            kind=n.kind,
            issuer=n.issuer,
            published_on=n.published_on,
            valid_from=n.valid_from,
            valid_to=n.valid_to,
            source_url=n.source_url,
            notes=n.notes,
            archived=n.archived,
            version=n.version,
            file=NormFileOut(
                original_name=n.file.original_name,
                size_bytes=n.file.size_bytes,
                url=file_url(n.id),
            )
            if n.file
            else None,
            linked_rules=[LinkedRuleOut.of(r) for r in found.rules],
        )
