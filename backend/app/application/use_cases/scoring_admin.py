"""Scoring table catalog (TAB-08) and administration (ADM-01..11) use cases.

Every administration write is ADMIN-only and audited (entities `scoring_table` and
`scoring_version`) in the same transaction as the change.
"""

import copy
import uuid
from collections.abc import Callable, Collection, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from app.application.services.audit_service import AuditService
from app.application.services.criteria_csv import CsvError, parse_criteria_csv
from app.application.use_cases.users import require_admin
from app.domain.entities.audit import AuditAction, AuditEvent
from app.domain.entities.scoring import (
    ScoringCriterion,
    ScoringGroup,
    ScoringMode,
    ScoringTableVersion,
    TableStatus,
)
from app.domain.entities.user import User
from app.domain.errors import Conflict, DomainError, NotFound, ValidationFailed
from app.domain.repositories.ports import ScoringTableRecord, UnitOfWork
from app.domain.rules.scoring_table_guards import (
    Blocker,
    TableFacts,
    VersionFacts,
    has_later_version,
    table_archive_blockers,
    table_delete_blockers,
    version_delete_blockers,
)

VERSION_NOT_FOUND = "Versão da tabela de pontuação não encontrada"
TABLE_NOT_FOUND = "Tabela de pontuação não encontrada"
TABLE_ENTITY = "scoring_table"
VERSION_ENTITY = "scoring_version"
_ROMAN = ("I", "II", "III", "IV", "V", "VI", "VII", "VIII")


@dataclass(frozen=True)
class VersionView:
    version: ScoringTableVersion
    in_use: bool  # some process uses the version (the sense it always had)
    process_count: int = 0  # GTAB-10
    default_for_unit_ids: tuple[UUID, ...] = ()  # the units that have it as the one in use


@dataclass(frozen=True)
class TableView:
    table: ScoringTableRecord
    versions: list[VersionView]


@dataclass(frozen=True)
class _VersionFacts:
    process_counts: Mapping[UUID, int]
    default_units: Mapping[UUID, tuple[UUID, ...]]


def _facts(uow: UnitOfWork) -> _VersionFacts:
    """The process counts and the marks of all versions, in two reads (no query per version)."""
    marks: dict[UUID, list[UUID]] = {}
    for default in uow.scoring_tables.list_unit_defaults():
        marks.setdefault(default.version_id, []).append(default.unit_id)
    return _VersionFacts(
        uow.scoring_tables.version_process_counts(),
        {version_id: tuple(sorted(unit_ids)) for version_id, unit_ids in marks.items()},
    )


def _views(facts: _VersionFacts, versions) -> list[VersionView]:
    return [
        VersionView(
            v,
            facts.process_counts.get(v.id, 0) > 0,
            facts.process_counts.get(v.id, 0),
            facts.default_units.get(v.id, ()),
        )
        for v in versions
    ]


class ListScoringTables:
    def __init__(self, uow_factory: Callable[[], UnitOfWork]):
        self._uow_factory = uow_factory

    def execute(self) -> list[TableView]:
        with self._uow_factory() as uow:
            facts = _facts(uow)
            return [
                TableView(t, _views(facts, uow.scoring_tables.list_version_headers(t.id)))
                for t in uow.scoring_tables.list_tables()
            ]


class ListTableVersions:
    def __init__(self, uow_factory: Callable[[], UnitOfWork]):
        self._uow_factory = uow_factory

    def execute(self, table_id: UUID) -> list[VersionView]:
        with self._uow_factory() as uow:
            if uow.scoring_tables.get_table(table_id) is None:
                raise NotFound("Tabela de pontuação não encontrada")
            return _views(_facts(uow), uow.scoring_tables.list_version_headers(table_id))


class GetScoringVersion:
    def __init__(self, uow_factory: Callable[[], UnitOfWork]):
        self._uow_factory = uow_factory

    def execute(self, version_id: UUID) -> VersionView:
        with self._uow_factory() as uow:
            version = uow.scoring_tables.get_version(version_id)
            if version is None:
                raise NotFound("Versão da tabela de pontuação não encontrada")
            return _views(_facts(uow), [version])[0]


def _default_acronyms(uow: UnitOfWork, version_ids: Collection[UUID]) -> tuple[str, ...]:
    """The acronyms of the units that have one of the versions as the one in use, sorted."""
    acronyms = []
    for default in uow.scoring_tables.list_unit_defaults():
        if default.version_id in version_ids:
            unit = uow.units.get(default.unit_id)
            acronyms.append(unit.acronym if unit else str(default.unit_id))
    return tuple(sorted(acronyms))


@dataclass(frozen=True)
class ProtectedCatalog:
    """The table the seed recreates at every start: it and all its versions are never deleted
    (GTAB-42). The name comes from the wiring, so this layer reads no infrastructure data."""

    official_table_name: str

    def is_official(self, table_name: str) -> bool:
        return table_name.casefold() == self.official_table_name.casefold()


def _table_facts(
    uow: UnitOfWork, table: ScoringTableRecord, catalog: ProtectedCatalog | None = None
) -> TableFacts:
    """What the blocking rules read about a table (GTAB-25, GTAB-29), from the current state."""
    version_ids = {v.id for v in uow.scoring_tables.list_version_headers(table.id)}
    counts = uow.scoring_tables.version_process_counts()
    return TableFacts(
        is_official=catalog is not None and catalog.is_official(table.name),
        process_count=sum(counts.get(version_id, 0) for version_id in version_ids),
        default_unit_acronyms=_default_acronyms(uow, version_ids),
        table_archived=table.archived,
    )


def _version_facts(
    uow: UnitOfWork,
    version: ScoringTableVersion,
    table: ScoringTableRecord,
    catalog: ProtectedCatalog | None = None,
) -> VersionFacts:
    """What the blocking rules read about a version, from the current state."""
    repo = uow.scoring_tables
    siblings = repo.list_version_headers(table.id)
    return VersionFacts(
        process_count=repo.version_process_counts().get(version.id, 0),
        default_unit_acronyms=_default_acronyms(uow, {version.id}),
        replaces_other=version.id in repo.superseding_version_ids(),
        is_superseded=version.is_superseded,
        has_later_version=has_later_version(version, siblings),
        is_only_version=len(siblings) == 1,
        table_archived=table.archived,
        is_official=catalog is not None and catalog.is_official(table.name),
    )


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
    """The version that starts last, leaving out the superseded ones (GI-07)."""
    current = [v for v in versions if not v.is_superseded]
    return max(current, key=lambda v: v.valid_from, default=None)


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


_TEXT_FIELDS = ("description", "unit_label", "accepted_evidence", "rules", "review_note")
_DECIMAL_FIELDS = ("unit_points", "hours_per_block", "prep_ratio", "min_hours", "max_points")
EDITABLE_CRITERION_FIELDS = (
    *_TEXT_FIELDS,
    *_DECIMAL_FIELDS,
    "mode",
    "weeks_per_semester",
)


def _plain(value):
    if isinstance(value, Decimal):
        return format(value.normalize(), "f")
    return value


def _criterion_view(c: ScoringCriterion, fields) -> dict:
    return {
        f"criteria.{c.group_number}.{c.item_number}.{f}": _plain(getattr(c, f)) for f in fields
    }


def _coerce_change(field: str, value):
    if field == "mode":
        try:
            return ScoringMode(value)
        except ValueError:
            raise ValidationFailed("mode", "Modo de pontuação inválido") from None
    if field in _DECIMAL_FIELDS:
        if value is None:
            return None
        try:
            number = Decimal(str(value))
        except ArithmeticError:
            raise ValidationFailed(field, "Valor numérico inválido") from None
        if not number.is_finite() or number < 0:
            raise ValidationFailed(field, "Valor deve ser um número não negativo")
        return number
    if field == "weeks_per_semester":
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValidationFailed(field, "Valor deve ser um inteiro positivo")
        return value
    if field == "description" and not str(value or "").strip():
        raise ValidationFailed(field, "Descrição é obrigatória")
    if field == "review_note":
        return (str(value).strip() or None) if value is not None else None
    return "" if value is None else str(value)


class UpdateVersionCriteria:
    """ADM-03/04: edit one criterion of a version no process uses, citing the norm."""

    def __init__(self, uow_factory: Callable[[], UnitOfWork], audit: AuditService):
        self._uow_factory = uow_factory
        self._audit = audit

    def execute(
        self,
        actor: User,
        version_id: UUID,
        group: int,
        item: int,
        changes: dict,
        change_reference: str,
    ) -> VersionView:
        require_admin(actor)
        reference = (change_reference or "").strip()
        if not reference:
            raise ValidationFailed(
                "change_reference", "Referência normativa da alteração é obrigatória"
            )
        unknown = sorted(set(changes) - set(EDITABLE_CRITERION_FIELDS))
        if unknown:
            raise ValidationFailed("changes", f"Campo não editável: {', '.join(unknown)}")
        if not changes:
            raise ValidationFailed("changes", "Nenhuma alteração informada")
        values = {f: _coerce_change(f, v) for f, v in changes.items()}
        with self._uow_factory() as uow:
            version = uow.scoring_tables.get_version(version_id)
            if version is None:
                raise NotFound("Versão da tabela de pontuação não encontrada")
            current = version.get_criterion(group, item)
            if current is None:
                raise NotFound("Critério não encontrado")
            if version.is_superseded:
                raise Conflict(
                    "Versão substituída é somente leitura; altere a versão que a substitui"
                )
            if any(
                v.valid_from > version.valid_from
                for v in uow.scoring_tables.list_versions(version.table_id)
            ):
                raise Conflict(
                    "Versão anterior é somente leitura; altere a versão mais recente "
                    "ou crie uma nova versão"
                )
            if uow.scoring_tables.version_in_use(version_id):
                raise Conflict(
                    "Versão já usada por processos não pode ser alterada; "
                    "crie uma nova versão para alterar os critérios"
                )
            updated = replace(current, **values)
            uow.scoring_tables.update_criterion(version_id, updated)
            self._audit.record(
                uow,
                actor.id,
                VERSION_ENTITY,
                version_id,
                AuditAction.UPDATE,
                _criterion_view(current, values),
                _criterion_view(updated, values),
                justification=reference,
            )
            result = uow.scoring_tables.get_version(version_id)
            uow.commit()
        return VersionView(result, False)


def _overlaps(a: ScoringTableVersion, b: ScoringTableVersion) -> bool:
    starts_before_b_ends = b.valid_to is None or a.valid_from <= b.valid_to
    b_starts_before_a_ends = a.valid_to is None or b.valid_from <= a.valid_to
    return starts_before_b_ends and b_starts_before_a_ends


def close_open_version(
    uow: UnitOfWork,
    audit: AuditService,
    actor: User,
    existing: Sequence[ScoringTableVersion],
    new_valid_from: date,
) -> list[ScoringTableVersion]:
    """ADM-05/06: end the open-ended version the day before the new one starts.

    Raises Conflict, changing nothing, if a process that chose the open version has an
    interstice ending on or after the new start. Returns `existing` with the closed version.
    """
    open_version = next((v for v in existing if v.valid_to is None), None)
    if open_version is None or new_valid_from <= open_version.valid_from:
        return list(existing)  # no open version, or not a successor: overlap check decides
    if uow.scoring_tables.version_in_use_ending_from(open_version.id, new_valid_from):
        raise Conflict(
            f"Há processo que escolheu a versão \"{open_version.name}\" com interstício "
            f"terminando a partir de {new_valid_from:%d/%m/%Y}; encerrá-la mudaria a "
            "versão aplicável a ele"
        )
    closed = replace(open_version, valid_to=new_valid_from - timedelta(days=1))
    uow.scoring_tables.update_version(closed)
    audit.record(
        uow,
        actor.id,
        VERSION_ENTITY,
        closed.id,
        AuditAction.UPDATE,
        _audit_version(open_version),
        _audit_version(closed),
    )
    return [closed if v.id == closed.id else v for v in existing]


def add_version_closing_open(
    uow: UnitOfWork, audit: AuditService, actor: User, version: ScoringTableVersion, extra: dict
) -> None:
    """Close the open version if needed, reject overlaps, persist and audit the new version."""
    # A superseded version is out of the open-version and overlap rules (GI-07).
    existing = [
        v for v in uow.scoring_tables.list_versions(version.table_id) if not v.is_superseded
    ]
    existing = close_open_version(uow, audit, actor, existing, version.valid_from)
    for other in existing:
        if _overlaps(version, other):
            raise Conflict(f'Vigência sobrepõe a versão "{other.name}"')
    uow.scoring_tables.add_version(version)
    audit.record(
        uow,
        actor.id,
        VERSION_ENTITY,
        version.id,
        AuditAction.CREATE,
        {},
        {**_audit_version(version), **extra},
        justification=version.norm_reference,
    )


class CreateVersionFrom:
    """ADM-05..07: a new version copying groups, criteria and minimums of another."""

    def __init__(self, uow_factory: Callable[[], UnitOfWork], audit: AuditService):
        self._uow_factory = uow_factory
        self._audit = audit

    def execute(
        self,
        actor: User,
        table_id: UUID,
        source_version_id: UUID,
        valid_from: date,
        valid_to: date | None,
        norm_reference: str,
        version_name: str | None = None,
        status: TableStatus = TableStatus.PENDENTE_VALIDACAO,
    ) -> VersionView:
        require_admin(actor)
        reference = check_validity(valid_from, valid_to, norm_reference)
        with self._uow_factory() as uow:
            if uow.scoring_tables.get_table(table_id) is None:
                raise NotFound("Tabela de pontuação não encontrada")
            source = uow.scoring_tables.get_version(source_version_id)
            if source is None:
                raise NotFound("Versão de origem não encontrada")
            version = replace(
                source,
                id=uuid.uuid4(),
                table_id=table_id,
                name=(version_name or "").strip() or default_version_name(valid_from),
                valid_from=valid_from,
                valid_to=valid_to,
                norm_reference=reference,
                status=status,
                minimums=copy.deepcopy(source.minimums),
            )
            add_version_closing_open(
                uow, self._audit, actor, version, {"copied_from_version_id": source.id}
            )
            uow.commit()
        return VersionView(version, False)


class InvalidCsv(DomainError):
    """ADM-09: every invalid line and field of the file (HTTP 422, nothing created)."""

    def __init__(self, errors: Sequence[CsvError]):
        super().__init__(f"{len(errors)} erro(s) no arquivo CSV")
        self.errors = list(errors)


class ImportCriteriaCsv:
    """ADM-08/09: all-or-nothing import of a CSV as a new version of the table.

    Group names, group limits and `counts_in_total` come from the table's latest version;
    the criteria come only from the file. CARGA_SEMANAL rows have no columns for weeks and
    preparation, so they take both from the same item of the latest version.
    """

    def __init__(self, uow_factory: Callable[[], UnitOfWork], audit: AuditService):
        self._uow_factory = uow_factory
        self._audit = audit

    def execute(
        self,
        actor: User,
        table_id: UUID,
        valid_from: date,
        valid_to: date | None,
        norm_reference: str,
        csv_text: str,
        status: TableStatus = TableStatus.PENDENTE_VALIDACAO,
        version_name: str | None = None,
    ) -> VersionView:
        require_admin(actor)
        reference = check_validity(valid_from, valid_to, norm_reference)
        with self._uow_factory() as uow:
            if uow.scoring_tables.get_table(table_id) is None:
                raise NotFound("Tabela de pontuação não encontrada")
            base = latest_version(uow.scoring_tables.list_versions(table_id))
            parsed = parse_criteria_csv(csv_text)
            errors = list(parsed.errors)
            criteria = []
            for criterion, line in zip(parsed.criteria, parsed.lines, strict=True):
                if criterion.mode is ScoringMode.CARGA_SEMANAL:
                    previous = base and base.get_criterion(
                        criterion.group_number, criterion.item_number
                    )
                    if previous is None or previous.weeks_per_semester is None:
                        errors.append(
                            CsvError(
                                line,
                                "modo",
                                "CARGA_SEMANAL exige semanas e preparação, que o CSV não traz; "
                                "o item precisa existir na última versão com esses valores",
                            )
                        )
                        continue
                    criterion = replace(
                        criterion,
                        weeks_per_semester=previous.weeks_per_semester,
                        prep_ratio=previous.prep_ratio,
                    )
                criteria.append(criterion)
            if errors:
                raise InvalidCsv(sorted(errors, key=lambda e: e.line))
            groups = []
            for number, template in enumerate(empty_groups(), start=1):
                group = (base and base.get_group(number)) or template
                groups.append(
                    replace(
                        group,
                        criteria=tuple(
                            sorted(
                                (c for c in criteria if c.group_number == number),
                                key=lambda c: c.item_number,
                            )
                        ),
                    )
                )
            version = ScoringTableVersion(
                id=uuid.uuid4(),
                table_id=table_id,
                name=(version_name or "").strip() or default_version_name(valid_from),
                valid_from=valid_from,
                valid_to=valid_to,
                norm_reference=reference,
                status=status,
                groups=tuple(groups),
                minimums=copy.deepcopy(base.minimums) if base else None,
                notes=base.notes if base else None,
            )
            add_version_closing_open(
                uow, self._audit, actor, version, {"imported_criteria": len(criteria)}
            )
            uow.commit()
        return VersionView(version, False)


class SetTableUnits:
    """ADM-01: replace the academic units a table is associated with."""

    def __init__(self, uow_factory: Callable[[], UnitOfWork], audit: AuditService):
        self._uow_factory = uow_factory
        self._audit = audit

    def execute(self, actor: User, table_id: UUID, unit_ids: Sequence[UUID]) -> TableView:
        require_admin(actor)
        with self._uow_factory() as uow:
            before = uow.scoring_tables.get_table(table_id)
            if before is None:
                raise NotFound("Tabela de pontuação não encontrada")
            units = _check_units(uow, unit_ids)
            uow.scoring_tables.set_table_units(table_id, units)
            after = uow.scoring_tables.get_table(table_id)
            self._audit.record(
                uow,
                actor.id,
                TABLE_ENTITY,
                table_id,
                AuditAction.UPDATE,
                _audit_table(before),
                _audit_table(after),
            )
            view = TableView(after, _views(_facts(uow), uow.scoring_tables.list_versions(table_id)))
            uow.commit()
        return view


class ArchiveScoringTable:
    """GTAB-23, GTAB-25: archive or unarchive a table; it acts at once, without justification.

    The table is locked before the marks are read, so a mark that is being written either
    commits first (the archiving is refused) or waits and finds the table archived (it is
    refused, GTAB-24). Unarchiving never marks a version again.
    """

    def __init__(self, uow_factory: Callable[[], UnitOfWork], audit: AuditService):
        self._uow_factory = uow_factory
        self._audit = audit

    def execute(self, actor: User, table_id: UUID, archive: bool) -> TableView:
        require_admin(actor)
        with self._uow_factory() as uow:
            repo = uow.scoring_tables
            if not repo.lock_table(table_id):
                raise NotFound("Tabela de pontuação não encontrada")
            table = repo.get_table(table_id)
            if table is None:
                raise NotFound("Tabela de pontuação não encontrada")
            if archive and not table.archived:
                blockers = table_archive_blockers(_table_facts(uow, table))
                if blockers:
                    raise Conflict(blockers[0].message, code=blockers[0].code)
            if table.archived != archive:
                repo.set_table_archived(table_id, archive)
            self._audit.record(
                uow,
                actor.id,
                TABLE_ENTITY,
                table_id,
                AuditAction.ARCHIVE if archive else AuditAction.UPDATE,
                {"archived": table.archived},
                {"archived": archive},
            )
            view = TableView(
                repo.get_table(table_id),
                _views(_facts(uow), repo.list_version_headers(table_id)),
            )
            uow.commit()
        return view


@dataclass(frozen=True)
class VersionDeletePreview:
    name: str
    criteria: int
    blocked: list[Blocker]


class PreviewDeleteVersion:
    """GTAB-30: what a deletion would remove and what blocks it, before the click."""

    def __init__(self, uow_factory: Callable[[], UnitOfWork], catalog: ProtectedCatalog):
        self._uow_factory = uow_factory
        self._catalog = catalog

    def execute(self, version_id: UUID) -> VersionDeletePreview:
        with self._uow_factory() as uow:
            repo = uow.scoring_tables
            version = repo.get_version(version_id)
            table = repo.get_table(version.table_id) if version else None
            if version is None or table is None:
                raise NotFound("Versão da tabela de pontuação não encontrada")
            return VersionDeletePreview(
                version.name,
                repo.count_criteria(version_id),
                version_delete_blockers(_version_facts(uow, version, table, self._catalog)),
            )


class DeleteScoringVersion:
    """GTAB-26, GTAB-27, GTAB-31, GTAB-32: delete a version nothing depends on, at once.

    The table and the version are locked (in this order) and every fact is read again under
    the locks, so a process that chooses the version, or a unit that marks it, either commits
    first (the deletion is refused) or waits and finds it deleted. A foreign key violation that
    still escapes is a 409. The audit events are never deleted.
    """

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        audit: AuditService,
        catalog: ProtectedCatalog,
    ):
        self._uow_factory = uow_factory
        self._audit = audit
        self._catalog = catalog

    def execute(self, actor: User, version_id: UUID) -> None:
        require_admin(actor)
        with self._uow_factory() as uow:
            repo = uow.scoring_tables
            version = repo.get_version(version_id)
            if version is None or version.table_id is None:
                raise NotFound(VERSION_NOT_FOUND)
            if not repo.lock_table(version.table_id) or not repo.lock_version(version_id):
                raise NotFound(VERSION_NOT_FOUND)
            version = repo.get_version(version_id)
            table = repo.get_table(version.table_id) if version else None
            if version is None or table is None:
                raise NotFound(VERSION_NOT_FOUND)
            blockers = version_delete_blockers(_version_facts(uow, version, table, self._catalog))
            if blockers:
                raise Conflict(blockers[0].message, code=blockers[0].code)
            before = {
                **_audit_version(version),
                "norm_code": version.norm_code,
                "criteria": repo.count_criteria(version_id),
            }
            self._reopen_previous(uow, actor, version)
            repo.delete_version(version_id)
            self._audit.record(
                uow, actor.id, VERSION_ENTITY, version_id, AuditAction.DELETE, before, {}
            )
            uow.commit()

    def _reopen_previous(
        self, uow: UnitOfWork, actor: User, deleted: ScoringTableVersion
    ) -> None:
        """The latest version closed the previous one the day before it started (ADM-05):
        deleting it gives the previous one the end of validity of the deleted one back, so the
        table is not left without a current version (A11)."""
        siblings = uow.scoring_tables.list_version_headers(deleted.table_id)
        if has_later_version(deleted, siblings):
            return
        day_before = deleted.valid_from - timedelta(days=1)
        closed_by_it = [
            v
            for v in siblings
            if v.id != deleted.id and not v.is_superseded and v.valid_to == day_before
        ]
        if not closed_by_it:
            return
        previous = max(closed_by_it, key=lambda v: v.valid_from)
        reopened = replace(previous, valid_to=deleted.valid_to)
        uow.scoring_tables.update_version(reopened)
        self._audit.record(
            uow,
            actor.id,
            VERSION_ENTITY,
            previous.id,
            AuditAction.UPDATE,
            _audit_version(previous),
            _audit_version(reopened),
        )


@dataclass(frozen=True)
class PreviewUnit:
    id: UUID
    acronym: str


@dataclass(frozen=True)
class TableDeletePreview:
    name: str
    versions: int
    criteria: int
    units: list[PreviewUnit]
    blocked: list[Blocker]


class PreviewDeleteTable:
    """GTAB-30: what deleting the table removes and what blocks it, before the click."""

    def __init__(self, uow_factory: Callable[[], UnitOfWork], catalog: ProtectedCatalog):
        self._uow_factory = uow_factory
        self._catalog = catalog

    def execute(self, table_id: UUID) -> TableDeletePreview:
        with self._uow_factory() as uow:
            repo = uow.scoring_tables
            table = repo.get_table(table_id)
            if table is None:
                raise NotFound(TABLE_NOT_FOUND)
            versions = repo.list_version_headers(table_id)
            units = [uow.units.get(unit_id) for unit_id in table.unit_ids]
            return TableDeletePreview(
                table.name,
                len(versions),
                sum(repo.count_criteria(v.id) for v in versions),
                [PreviewUnit(u.id, u.acronym) for u in units if u is not None],
                table_delete_blockers(_table_facts(uow, table, self._catalog)),
            )


class DeleteScoringTable:
    """GTAB-28, GTAB-29, GTAB-31, GTAB-32: delete a table and its versions in one transaction.

    The table and then all its versions (by id) are locked and every fact is read again under
    the locks, so a process that chooses a version, or a unit that marks one, either commits
    first (the deletion is refused) or waits and finds it deleted. The audit events stay.
    """

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        audit: AuditService,
        catalog: ProtectedCatalog,
    ):
        self._uow_factory = uow_factory
        self._audit = audit
        self._catalog = catalog

    def execute(self, actor: User, table_id: UUID) -> None:
        require_admin(actor)
        with self._uow_factory() as uow:
            repo = uow.scoring_tables
            if not repo.lock_table(table_id):
                raise NotFound(TABLE_NOT_FOUND)
            for version in sorted(repo.list_version_headers(table_id), key=lambda v: str(v.id)):
                repo.lock_version(version.id)
            table = repo.get_table(table_id)
            if table is None:
                raise NotFound(TABLE_NOT_FOUND)
            blockers = table_delete_blockers(_table_facts(uow, table, self._catalog))
            if blockers:
                raise Conflict(blockers[0].message, code=blockers[0].code)
            versions = repo.list_version_headers(table_id)
            before = {
                "name": table.name,
                "unit_ids": list(table.unit_ids),
                "versions": [
                    {
                        "id": v.id,
                        "name": v.name,
                        "valid_from": v.valid_from,
                        "valid_to": v.valid_to,
                        "norm_reference": v.norm_reference,
                        "status": v.status,
                    }
                    for v in versions
                ],
                "criteria": sum(repo.count_criteria(v.id) for v in versions),
            }
            repo.delete_table(table_id)
            self._audit.record(
                uow, actor.id, TABLE_ENTITY, table_id, AuditAction.DELETE, before, {}
            )
            uow.commit()


@dataclass(frozen=True)
class TableHistory:
    versions: list[VersionView]
    events: list[AuditEvent]  # table and version events, chronological


class GetTableHistory:
    """ADM-10: every version with validity, reference and status, plus all audit events."""

    def __init__(self, uow_factory: Callable[[], UnitOfWork]):
        self._uow_factory = uow_factory

    def execute(self, table_id: UUID) -> TableHistory:
        with self._uow_factory() as uow:
            if uow.scoring_tables.get_table(table_id) is None:
                raise NotFound("Tabela de pontuação não encontrada")
            versions = uow.scoring_tables.list_versions(table_id)
            events = list(uow.audit.list_for(TABLE_ENTITY, str(table_id)))
            for v in versions:
                events.extend(uow.audit.list_for(VERSION_ENTITY, str(v.id)))
            events.sort(key=lambda e: (e.occurred_at, e.id or 0))
            return TableHistory(_views(_facts(uow), versions), events)
