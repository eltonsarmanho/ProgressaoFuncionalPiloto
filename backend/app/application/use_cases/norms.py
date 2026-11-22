"""Norm base: register, edit, archive, attach the PDF and list with the linked rules
(NBASE-01..10, NLIST-01, NLIST-02).

Writes are for the ADMIN only; every authenticated person reads. A norm is never deleted: it is
archived and keeps the rules linked to it (NBASE-08).
"""

import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path
from uuid import UUID

from app.application.services.audit_service import AuditService
from app.application.use_cases.documents import UploadRejected
from app.application.use_cases.users import require_admin
from app.domain.entities.audit import AuditAction
from app.domain.entities.norm import Norm, NormKind
from app.domain.entities.user import User
from app.domain.errors import NotFound, ValidationFailed
from app.domain.repositories.ports import (
    FileInspector,
    NormFileStorage,
    StagedNormFile,
    UnitOfWork,
)
from app.domain.rules.norm_rules import validate_norm
from app.domain.rules.upload_validation import (
    UploadLimits,
    extension_of,
    safe_display_name,
    validate_upload,
)

ENTITY = "norm"
MAX_FILE_BYTES = 20 * 1024 * 1024
# A norm PDF can be long; only the size and the file structure are limited (NBASE-06).
_FILE_LIMITS = UploadLimits(max_file_bytes=MAX_FILE_BYTES, max_pages=100_000)
RULE_CAREER = "CARREIRA"
RULE_TABLE = "TABELA"
RULE_TITRATION = "TITULACAO"


@dataclass(frozen=True)
class NormFields:
    """What the ADMIN edits in a norm; the code is chosen once, at creation."""

    title: str = ""
    kind: NormKind | None = None
    issuer: str = ""
    published_on: date | None = None
    valid_from: date | None = None
    valid_to: date | None = None
    source_url: str | None = None
    notes: str | None = None


@dataclass(frozen=True)
class LinkedRule:
    """A rule of the system that cites the norm: a career structure, a scoring table version or
    the titration rules of a career structure."""

    kind: str
    name: str
    detail: str | None = None


@dataclass(frozen=True)
class NormWithLinks:
    norm: Norm
    rules: tuple[LinkedRule, ...] = ()


def _blank_to_none(value: str | None) -> str | None:
    value = (value or "").strip()
    return value or None


def _validated(code: str, data: NormFields) -> dict:
    fields = {
        "code": (code or "").strip(),
        "title": (data.title or "").strip(),
        "kind": data.kind,
        "issuer": (data.issuer or "").strip(),
        "published_on": data.published_on,
        "valid_from": data.valid_from,
        "valid_to": data.valid_to,
        "source_url": _blank_to_none(data.source_url),
        "notes": _blank_to_none(data.notes),
    }
    errors = validate_norm(fields)
    if errors:
        raise ValidationFailed(errors[0].field, errors[0].message)
    return fields


def _audit_view(norm: Norm) -> dict:
    view = {
        "code": norm.code,
        "title": norm.title,
        "kind": norm.kind,
        "issuer": norm.issuer,
        "published_on": norm.published_on,
        "valid_from": norm.valid_from,
        "valid_to": norm.valid_to,
        "source_url": norm.source_url,
        "notes": norm.notes,
        "archived": norm.archived,
        "file_original_name": None,
        "file_size_bytes": None,
        "file_sha256": None,
    }
    if norm.file is not None:
        view["file_original_name"] = norm.file.original_name
        view["file_size_bytes"] = norm.file.size_bytes
        view["file_sha256"] = norm.file.sha256
    return view


def _existing(uow: UnitOfWork, norm_id: UUID) -> Norm:
    norm = uow.norms.get(norm_id)
    if norm is None:
        raise NotFound("Norma não encontrada")
    return norm


def _rules_by_code(
    uow: UnitOfWork, structure_codes: Sequence[str]
) -> dict[str, list[LinkedRule]]:
    """NLIST-01: the career structures, titration rules and scoring table versions, by the
    code of the norm they cite."""
    rules: dict[str, list[LinkedRule]] = {}
    for structure in structure_codes:
        for version in uow.career_versions.list_versions(structure):
            if version.norm_code:
                rules.setdefault(version.norm_code, []).append(
                    LinkedRule(RULE_CAREER, version.name)
                )
            required = [c for c in version.classes if c.required_titration is not None]
            if version.required_titration_norm_code and required:
                detail = "; ".join(
                    f"classe {c.code}: {c.required_titration.value}"
                    for c in required
                    if c.required_titration is not None
                )
                rules.setdefault(version.required_titration_norm_code, []).append(
                    LinkedRule(RULE_TITRATION, version.name, detail)
                )
    for table in uow.scoring_tables.list_tables():
        for table_version in uow.scoring_tables.list_versions(table.id):
            if table_version.norm_code:
                rules.setdefault(table_version.norm_code, []).append(
                    LinkedRule(
                        RULE_TABLE,
                        table_version.name,
                        f"vigência a partir de {table_version.valid_from:%d/%m/%Y}",
                    )
                )
    return rules


class _Reader:
    def __init__(
        self, uow_factory: Callable[[], UnitOfWork], structure_codes: Sequence[str]
    ):
        self._uow_factory = uow_factory
        self._structure_codes = tuple(structure_codes)

    def _with_links(self, uow: UnitOfWork, norms: Sequence[Norm]) -> list[NormWithLinks]:
        rules = _rules_by_code(uow, self._structure_codes)
        return [NormWithLinks(n, tuple(rules.get(n.code, ()))) for n in norms]


class ListNorms(_Reader):
    def execute(self, actor: User, include_archived: bool = False) -> list[NormWithLinks]:
        with self._uow_factory() as uow:
            return self._with_links(uow, uow.norms.list(include_archived))


class GetNorm(_Reader):
    def execute(self, actor: User, norm_id: UUID) -> NormWithLinks:
        with self._uow_factory() as uow:
            return self._with_links(uow, [_existing(uow, norm_id)])[0]


class CreateNorm:
    def __init__(self, uow_factory: Callable[[], UnitOfWork], audit: AuditService):
        self._uow_factory = uow_factory
        self._audit = audit

    def execute(self, actor: User, code: str, data: NormFields) -> Norm:
        require_admin(actor)
        fields = _validated(code, data)
        with self._uow_factory() as uow:
            if uow.norms.get_by_code(fields["code"]) is not None:
                raise ValidationFailed("code", "Já existe uma norma com este código")
            norm = Norm(id=uuid.uuid4(), **fields)
            uow.norms.add(norm)
            self._audit.record(
                uow, actor.id, ENTITY, norm.id, AuditAction.CREATE, {}, _audit_view(norm)
            )
            uow.commit()
        return norm


class UpdateNorm:
    def __init__(self, uow_factory: Callable[[], UnitOfWork], audit: AuditService):
        self._uow_factory = uow_factory
        self._audit = audit

    def execute(
        self, actor: User, norm_id: UUID, data: NormFields, expected_version: int
    ) -> Norm:
        require_admin(actor)
        with self._uow_factory() as uow:
            current = _existing(uow, norm_id)
            fields = _validated(current.code, data)
            fields.pop("code")
            norm = replace(current, **fields)
            uow.norms.update(norm, expected_version)
            self._audit.record(
                uow,
                actor.id,
                ENTITY,
                norm.id,
                AuditAction.UPDATE,
                _audit_view(current),
                _audit_view(norm),
            )
            uow.commit()
        return norm


class ArchiveNorm:
    def __init__(self, uow_factory: Callable[[], UnitOfWork], audit: AuditService):
        self._uow_factory = uow_factory
        self._audit = audit

    def execute(self, actor: User, norm_id: UUID, expected_version: int) -> Norm:
        require_admin(actor)
        with self._uow_factory() as uow:
            current = _existing(uow, norm_id)
            norm = replace(current, archived=True)
            uow.norms.update(norm, expected_version)
            self._audit.record(
                uow,
                actor.id,
                ENTITY,
                norm.id,
                AuditAction.ARCHIVE,
                _audit_view(current),
                _audit_view(norm),
            )
            uow.commit()
        return norm


class AttachNormFile:
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        audit: AuditService,
        storage: NormFileStorage,
        inspector: FileInspector,
    ):
        self._uow_factory = uow_factory
        self._audit = audit
        self._storage = storage
        self._inspector = inspector

    def _check_pdf(self, staged: StagedNormFile) -> None:
        if extension_of(staged.original_name) != ".pdf":
            raise UploadRejected("EXTENSAO_INVALIDA", "Envie um arquivo PDF.")
        facts = self._inspector.inspect(staged.path)
        rejections = validate_upload(facts, None, ".pdf", _FILE_LIMITS)
        if rejections:
            first = rejections[0]
            message = (
                f"O PDF passa do limite de {MAX_FILE_BYTES // (1024 * 1024)} MB."
                if first.code == "ARQUIVO_GRANDE"
                else first.message
            )
            raise UploadRejected(first.code, message)

    def execute(
        self, actor: User, norm_id: UUID, staged: StagedNormFile, expected_version: int
    ) -> Norm:
        """Validates, stores the new file, commits, and only then removes the previous one, so a
        failure at any step leaves the record and the previous file as they were."""
        require_admin(actor)
        staged = replace(staged, original_name=safe_display_name(staged.original_name))
        stored = None
        try:
            with self._uow_factory() as uow:
                current = _existing(uow, norm_id)
                self._check_pdf(staged)
                stored = self._storage.save(staged)
                norm = replace(current, file=stored)
                uow.norms.update(norm, expected_version)
                self._audit.record(
                    uow,
                    actor.id,
                    ENTITY,
                    norm.id,
                    AuditAction.UPDATE,
                    _audit_view(current),
                    _audit_view(norm),
                )
                uow.commit()
        except Exception:
            if stored is not None:
                self._storage.delete(stored.internal_name)
            raise
        if current.file is not None:
            self._storage.delete(current.file.internal_name)
        return norm


class DownloadNormFile:
    def __init__(self, uow_factory: Callable[[], UnitOfWork], storage: NormFileStorage):
        self._uow_factory = uow_factory
        self._storage = storage

    def execute(self, actor: User, norm_id: UUID) -> tuple[Path, str]:
        with self._uow_factory() as uow:
            norm = _existing(uow, norm_id)
        if norm.file is None:
            raise NotFound("A norma não tem arquivo")
        return self._storage.open(norm.file.internal_name), norm.file.original_name
