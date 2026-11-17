"""Scoring table catalog (TAB-08) and administration (ADM-01..11) use cases.

Every administration write is ADMIN-only and audited (entities `scoring_table` and
`scoring_version`) in the same transaction as the change.
"""

import copy
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from datetime import date
from uuid import UUID

from app.application.services.audit_service import AuditService
from app.application.use_cases.users import require_admin
from app.domain.entities.audit import AuditAction
from app.domain.entities.scoring import (
    ScoringGroup,
    ScoringTableVersion,
    TableStatus,
)
from app.domain.entities.user import User
from app.domain.errors import Conflict, NotFound, ValidationFailed
from app.domain.repositories.ports import ScoringTableRecord, UnitOfWork

TABLE_ENTITY = "scoring_table"
VERSION_ENTITY = "scoring_version"
_ROMAN = ("I", "II", "III", "IV", "V", "VI", "VII", "VIII")


@dataclass(frozen=True)
class VersionView:
    version: ScoringTableVersion
    in_use: bool


@dataclass(frozen=True)
class TableView:
    table: ScoringTableRecord
    versions: list[VersionView]


def _views(uow: UnitOfWork, versions) -> list[VersionView]:
    return [VersionView(v, uow.scoring_tables.version_in_use(v.id)) for v in versions]


class ListScoringTables:
    def __init__(self, uow_factory: Callable[[], UnitOfWork]):
        self._uow_factory = uow_factory

    def execute(self) -> list[TableView]:
        with self._uow_factory() as uow:
            return [
                TableView(t, _views(uow, uow.scoring_tables.list_versions(t.id)))
                for t in uow.scoring_tables.list_tables()
            ]


class ListTableVersions:
    def __init__(self, uow_factory: Callable[[], UnitOfWork]):
        self._uow_factory = uow_factory

    def execute(self, table_id: UUID) -> list[VersionView]:
        with self._uow_factory() as uow:
            if uow.scoring_tables.get_table(table_id) is None:
                raise NotFound("Tabela de pontuação não encontrada")
            return _views(uow, uow.scoring_tables.list_versions(table_id))


class GetScoringVersion:
    def __init__(self, uow_factory: Callable[[], UnitOfWork]):
        self._uow_factory = uow_factory

    def execute(self, version_id: UUID) -> VersionView:
        with self._uow_factory() as uow:
            version = uow.scoring_tables.get_version(version_id)
            if version is None:
                raise NotFound("Versão da tabela de pontuação não encontrada")
            return _views(uow, [version])[0]


def _audit_table(table: ScoringTableRecord) -> dict:
    return {"name": table.name, "unit_ids": list(table.unit_ids)}


def _audit_version(v: ScoringTableVersion) -> dict:
    return {
        "table_id": v.table_id,
        "name": v.name,
        "valid_from": v.valid_from,
        "valid_to": v.valid_to,
        "norm_reference": v.norm_reference,
        "status": v.status,
    }


def _check_name(uow: UnitOfWork, name: str) -> str:
    name = name.strip()
    if not name:
        raise ValidationFailed("name", "Nome da tabela é obrigatório")
    if any(t.name.casefold() == name.casefold() for t in uow.scoring_tables.list_tables()):
        raise ValidationFailed("name", "Já existe uma tabela com este nome")
    return name


def _check_units(uow: UnitOfWork, unit_ids: Sequence[UUID]) -> tuple[UUID, ...]:
    unique = tuple(dict.fromkeys(unit_ids))
    for unit_id in unique:
        if uow.units.get(unit_id) is None:
            raise ValidationFailed("unit_ids", "Unidade acadêmica não encontrada")
    return unique


def check_validity(valid_from: date, valid_to: date | None, norm_reference: str) -> str:
    reference = norm_reference.strip()
    if not reference:
        raise ValidationFailed("norm_reference", "Referência normativa é obrigatória")
    if valid_to is not None and valid_to < valid_from:
        raise ValidationFailed("valid_to", "Fim da vigência anterior ao início")
    return reference


def default_version_name(valid_from: date) -> str:
    return f"Vigente desde {valid_from:%d/%m/%Y}"


def empty_groups() -> tuple[ScoringGroup, ...]:
    return tuple(ScoringGroup(number=i + 1, name=f"Grupo {r}") for i, r in enumerate(_ROMAN))


def latest_version(versions: Sequence[ScoringTableVersion]) -> ScoringTableVersion | None:
    return max(versions, key=lambda v: v.valid_from, default=None)


class CreateScoringTable:
    def __init__(self, uow_factory: Callable[[], UnitOfWork], audit: AuditService):
        self._uow_factory = uow_factory
        self._audit = audit

    def execute(
        self,
        actor: User,
        name: str,
        unit_ids: Sequence[UUID],
        valid_from: date,
        valid_to: date | None,
        norm_reference: str,
        version_name: str | None = None,
        status: TableStatus = TableStatus.PENDENTE_VALIDACAO,
        base_version_id: UUID | None = None,
    ) -> TableView:
        require_admin(actor)
        reference = check_validity(valid_from, valid_to, norm_reference)
        with self._uow_factory() as uow:
            name = _check_name(uow, name)
            units = _check_units(uow, unit_ids)
            groups, minimums, notes = empty_groups(), None, None
            if base_version_id is not None:
                base = uow.scoring_tables.get_version(base_version_id)
                if base is None:
                    raise ValidationFailed("base_version_id", "Versão base não encontrada")
                groups, minimums, notes = base.groups, copy.deepcopy(base.minimums), base.notes
            table = ScoringTableRecord(id=uuid.uuid4(), name=name, unit_ids=units)
            version = ScoringTableVersion(
                id=uuid.uuid4(),
                table_id=table.id,
                name=(version_name or "").strip() or default_version_name(valid_from),
                valid_from=valid_from,
                valid_to=valid_to,
                norm_reference=reference,
                status=status,
                groups=groups,
                minimums=minimums,
                notes=notes,
            )
            uow.scoring_tables.add_table(table)
            uow.scoring_tables.add_version(version)
            self._audit.record(
                uow, actor.id, TABLE_ENTITY, table.id, AuditAction.CREATE, {}, _audit_table(table)
            )
            self._audit.record(
                uow,
                actor.id,
                VERSION_ENTITY,
                version.id,
                AuditAction.CREATE,
                {},
                _audit_version(version),
                justification=reference,
            )
            uow.commit()
        return TableView(table, [VersionView(version, False)])


class DuplicateScoringTable:
    """ADM-02: a new, independent table holding a copy of the source's latest version."""

    def __init__(self, uow_factory: Callable[[], UnitOfWork], audit: AuditService):
        self._uow_factory = uow_factory
        self._audit = audit

    def execute(
        self,
        actor: User,
        source_table_id: UUID,
        new_name: str,
        unit_ids: Sequence[UUID] = (),
    ) -> TableView:
        require_admin(actor)
        with self._uow_factory() as uow:
            if uow.scoring_tables.get_table(source_table_id) is None:
                raise NotFound("Tabela de pontuação não encontrada")
            source = latest_version(uow.scoring_tables.list_versions(source_table_id))
            if source is None:
                raise Conflict("A tabela de origem não tem versão para copiar")
            name = _check_name(uow, new_name)
            units = _check_units(uow, unit_ids)
            table = ScoringTableRecord(id=uuid.uuid4(), name=name, unit_ids=units)
            version = replace(
                source,
                id=uuid.uuid4(),
                table_id=table.id,
                minimums=copy.deepcopy(source.minimums),
            )
            uow.scoring_tables.add_table(table)
            uow.scoring_tables.add_version(version)
            self._audit.record(
                uow,
                actor.id,
                TABLE_ENTITY,
                table.id,
                AuditAction.CREATE,
                {},
                {**_audit_table(table), "duplicated_from": source_table_id},
            )
            self._audit.record(
                uow,
                actor.id,
                VERSION_ENTITY,
                version.id,
                AuditAction.CREATE,
                {},
                {**_audit_version(version), "copied_from_version_id": source.id},
                justification=version.norm_reference,
            )
            uow.commit()
        return TableView(table, [VersionView(version, False)])
