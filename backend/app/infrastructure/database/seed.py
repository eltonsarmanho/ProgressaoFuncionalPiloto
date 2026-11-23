"""Idempotent reference data seed (CARR-02, UNIT-03, initial ADMIN).

Run with: python -m app.infrastructure.database.seed
"""

import json
import logging
import uuid
from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from app.application.services.audit_service import AuditService
from app.application.use_cases.scoring_adoption import AdoptSupersedingVersion
from app.application.use_cases.scoring_defaults import UNIT_DEFAULT_ENTITY
from app.domain.entities.academic_unit import AcademicUnit, UnitKind
from app.domain.entities.audit import AuditAction
from app.domain.entities.norm import Norm, NormKind
from app.domain.entities.scoring import (
    ScoringCriterion,
    ScoringGroup,
    ScoringMode,
    ScoringTableVersion,
    TableStatus,
)
from app.domain.entities.user import Role, User
from app.domain.repositories.ports import PasswordHasher, ScoringTableRecord
from app.domain.rules.career_catalog import MAGISTERIO_SUPERIOR_VERSIONS
from app.infrastructure.clock import SystemClock
from app.infrastructure.database.repositories import SqlUnitOfWork

logger = logging.getLogger(__name__)

STRUCTURE_CODE = "MAGISTERIO_SUPERIOR"
STRUCTURE_NAME = "Magistério Superior"

CAMPUS = ("Campus Universitário do Tocantins/Cametá", "CUNTINS", UnitKind.CAMPUS)
FASI = ("Faculdade de Sistemas de Informação", "FASI", UnitKind.FACULDADE)
IFCH = ("Instituto de Filosofia e Ciências Humanas", "IFCH", UnitKind.INSTITUTO)

SEED_DATA = Path(__file__).parent / "seed_data"
OFFICIAL_TABLE_SEED = "ufpa.json"
NORMS_SEED = "norms.json"
NORM_ENTITY = "norm"
CAREER_VERSION_ENTITY = "career_version"
SCORING_VERSION_ENTITY = "scoring_version"
LINK_JUSTIFICATION = "Ligação às normas (NLINK-01, NLINK-02, NTIT-06)"
NORM_SEED_JUSTIFICATION = "Semente das normas (NBASE-11)"
OFFICIAL_TABLE_UNITS = ("FASI", "IFCH")
# Tables replaced by the official UFPA table (OFI-08, OFI-09): archived, never deleted.
LEGACY_TABLE_NAMES = ("Tabela de Pontuação do IFCH", "Tabela de Pontuação da FASI")


def _ensure_unit(uow: SqlUnitOfWork, spec: tuple[str, str, UnitKind], parent_id=None):
    name, acronym, kind = spec
    existing = next((u for u in uow.units.list() if u.acronym == acronym), None)
    if existing is not None:
        return existing
    unit = AcademicUnit(id=uuid.uuid4(), name=name, acronym=acronym, kind=kind, parent_id=parent_id)
    uow.units.add(unit)
    return unit


def seed_norms(uow: SqlUnitOfWork) -> None:
    """Insert the norms of `norms.json` whose code is missing (NBASE-11, NBASE-12).

    Works inside the caller's transaction and never commits. A norm that already exists, edited
    or not, is left exactly as it is; each insert is audited as a change by the system.
    """
    audit = AuditService(SystemClock())
    existing = {n.code for n in uow.norms.list(include_archived=True)}
    for data in json.loads((SEED_DATA / NORMS_SEED).read_text(encoding="utf-8")):
        if data["code"] in existing:
            continue
        norm = Norm(
            id=uuid.uuid4(),
            code=data["code"],
            title=data["title"],
            kind=NormKind(data["kind"]),
            issuer=data["issuer"],
            published_on=date.fromisoformat(data["published_on"]),
            source_url=data["source_url"],
            notes=data["notes"],
        )
        uow.norms.add(norm)
        audit.record(
            uow,
            None,
            NORM_ENTITY,
            norm.id,
            AuditAction.CREATE,
            {},
            {
                "code": norm.code,
                "title": norm.title,
                "kind": norm.kind,
                "issuer": norm.issuer,
                "published_on": norm.published_on,
                "source_url": norm.source_url,
                "notes": norm.notes,
            },
            NORM_SEED_JUSTIFICATION,
        )


def link_career_norms(uow: SqlUnitOfWork) -> None:
    """Link the stored career versions to their norms, filling only what is still null.

    Matches each stored version by name with the catalog. A norm code or a required titration
    already set (by the ADMIN, for instance) is never overwritten. Works inside the caller's
    transaction, never commits, and audits each changed version as a system change.
    """
    audit = AuditService(SystemClock())
    catalog = {v.name: v for v in MAGISTERIO_SUPERIOR_VERSIONS}
    for stored in uow.career_versions.list_versions(STRUCTURE_CODE):
        wanted = catalog.get(stored.name)
        if wanted is None or stored.id is None:
            continue
        norm_code = stored.norm_code or wanted.norm_code
        titration_norm_code = (
            stored.required_titration_norm_code or wanted.required_titration_norm_code
        )
        titrations = {
            c.code: c.required_titration
            for c in wanted.classes
            if c.required_titration is not None
            and (current := stored.get_class(c.code)) is not None
            and current.required_titration is None
        }
        if (
            norm_code == stored.norm_code
            and titration_norm_code == stored.required_titration_norm_code
            and not titrations
        ):
            continue
        uow.career_versions.set_links(stored.id, norm_code, titrations, titration_norm_code)
        audit.record(
            uow,
            None,
            CAREER_VERSION_ENTITY,
            stored.id,
            AuditAction.UPDATE,
            {
                "norm_code": stored.norm_code,
                "required_titration_norm_code": stored.required_titration_norm_code,
            },
            {"norm_code": norm_code, "required_titration_norm_code": titration_norm_code}
            | ({"required_titration": titrations} if titrations else {}),
            LINK_JUSTIFICATION,
        )


def seed_reference_data(
    uow: SqlUnitOfWork, admin_email: str, admin_password: str, hasher: PasswordHasher
) -> None:
    """Create whatever reference data is missing; never touches existing rows."""
    with uow:
        uow.career_versions.ensure_structure(STRUCTURE_CODE, STRUCTURE_NAME)
        existing = {v.name for v in uow.career_versions.list_versions(STRUCTURE_CODE)}
        for version in MAGISTERIO_SUPERIOR_VERSIONS:
            if version.name not in existing:
                uow.career_versions.add(STRUCTURE_CODE, version)

        campus = _ensure_unit(uow, CAMPUS)
        _ensure_unit(uow, FASI, parent_id=campus.id)
        _ensure_unit(uow, IFCH)
        seed_norms(uow)
        link_career_norms(uow)

        if uow.users.get_by_email(admin_email) is None:
            uow.users.add(
                User(
                    id=uuid.uuid4(),
                    email=admin_email,
                    name="Administrador",
                    role=Role.ADMIN,
                    password_hash=hasher.hash(admin_password),
                )
            )
        uow.commit()


def _decimal(value: Any) -> Decimal | None:
    return None if value is None else Decimal(str(value))


def _scoring_version(data: dict[str, Any], table_id: uuid.UUID) -> ScoringTableVersion:
    groups = []
    for g in data["groups"]:
        criteria = tuple(
            ScoringCriterion(
                group_number=g["number"],
                item_number=c["item_number"],
                description=c["description"],
                unit_label=c["unit_label"],
                mode=ScoringMode(c["mode"]),
                unit_points=_decimal(c["unit_points"]),
                hours_per_block=_decimal(c["hours_per_block"]),
                weeks_per_semester=c["weeks_per_semester"],
                prep_ratio=_decimal(c["prep_ratio"]),
                max_points=_decimal(c["max_points"]),
                accepted_evidence=c["accepted_evidence"],
                rules=c["rules"],
                review_note=c["review_note"],
                min_hours=_decimal(c.get("min_hours")),
            )
            for c in g["criteria"]
        )
        groups.append(
            ScoringGroup(
                number=g["number"],
                name=g["name"],
                counts_in_total=g["counts_in_total"],
                max_points=_decimal(g["max_points"]),
                criteria=criteria,
            )
        )
    return ScoringTableVersion(
        table_id=table_id,
        name=data["version_name"],
        valid_from=date.fromisoformat(data["valid_from"]),
        valid_to=date.fromisoformat(data["valid_to"]) if data["valid_to"] else None,
        norm_reference=data["norm_reference"],
        status=TableStatus(data["status"]),
        groups=tuple(groups),
        minimums=data["minimums"],
        notes=data["notes"],
        norm_code=data.get("norm_code"),
    )


def _official_table_data() -> dict[str, Any]:
    return json.loads((SEED_DATA / OFFICIAL_TABLE_SEED).read_text(encoding="utf-8"))


def link_table_norms(uow: SqlUnitOfWork) -> None:
    """Give the versions of the official table the norm code of `ufpa.json`, only where null.

    The archived IFCH and FASI tables are other tables and stay without a code. Works inside the
    caller's transaction, never commits, and audits each changed version as a system change.
    """
    data = _official_table_data()
    norm_code = data.get("norm_code")
    tables = uow.scoring_tables.list_tables()
    table = next((t for t in tables if t.name == data["table_name"]), None)
    if norm_code is None or table is None:
        return
    audit = AuditService(SystemClock())
    for version in uow.scoring_tables.list_versions(table.id):
        if version.norm_code is not None:
            continue
        uow.scoring_tables.update_version(replace(version, norm_code=norm_code))
        audit.record(
            uow,
            None,
            SCORING_VERSION_ENTITY,
            version.id,
            AuditAction.UPDATE,
            {"norm_code": None},
            {"norm_code": norm_code},
            LINK_JUSTIFICATION,
        )


def _archive_legacy_tables(uow: SqlUnitOfWork) -> None:
    """Archive the IFCH and FASI tables and detach their units (OFI-09).

    A table with any version chosen by a process stays exactly as it is.
    """
    for table in uow.scoring_tables.list_tables():
        if table.name not in LEGACY_TABLE_NAMES:
            continue
        if any(
            uow.scoring_tables.version_in_use(v.id)
            for v in uow.scoring_tables.list_versions(table.id)
        ):
            continue
        if not table.archived:
            uow.scoring_tables.set_table_archived(table.id, True)
        if table.unit_ids:
            uow.scoring_tables.set_table_units(table.id, ())


def seed_scoring_tables(uow: SqlUnitOfWork) -> None:
    """Create the official UFPA scoring table for FASI and IFCH and archive the old ones.

    OFI-01, OFI-08..OFI-11, GI-07, GI-10. Idempotent: an existing table keeps its units; an
    existing version is left untouched. When the version names one it supersedes (`supersedes`),
    that one is marked and the processes still editable move to the new one, in the same
    transaction (AdoptSupersedingVersion). Requires the units created by
    `seed_reference_data`.
    """
    with uow:
        units = {u.acronym: u for u in uow.units.list()}
        missing = [a for a in OFFICIAL_TABLE_UNITS if a not in units]
        if missing:
            raise LookupError(f"Unidade {missing[0]} não cadastrada; rode a semente de unidades")
        data = _official_table_data()
        table = next(
            (t for t in uow.scoring_tables.list_tables() if t.name == data["table_name"]), None
        )
        if table is None:
            table = ScoringTableRecord(
                id=uuid.uuid4(),
                name=data["table_name"],
                unit_ids=tuple(units[a].id for a in OFFICIAL_TABLE_UNITS),
            )
            uow.scoring_tables.add_table(table)
        existing = {v.name for v in uow.scoring_tables.list_versions(table.id)}
        if data["version_name"] not in existing:
            uow.scoring_tables.add_version(_scoring_version(data, table.id))
        link_table_norms(uow)
        AdoptSupersedingVersion(AuditService(SystemClock())).execute(
            uow, table.id, data.get("supersedes"), data["version_name"]
        )
        _archive_legacy_tables(uow)
        uow.commit()


def seed_unit_defaults(uow: SqlUnitOfWork) -> None:
    """Mark the current official version as in use of FASI and IFCH, once per unit (GTAB-09).

    Only a unit that has the official table associated, no version in use and no audit event of
    the entity `unit_scoring_default` is marked: a unit that the ADMIN cleared, or that lost its
    mark when its version was superseded, has an event and is left alone, so the seed never
    undoes what the ADMIN did. Each mark is audited as a system change. When the table, the
    version or the unit is missing, the version is superseded or the table is archived, the unit
    is not marked and the reason goes to the log: the seed runs under `set -eu` at the container
    start and must not fail here. Never called by `seed_scoring_tables`.
    """
    with uow:
        data = _official_table_data()
        units = {u.acronym: u for u in uow.units.list()}
        table = next(
            (t for t in uow.scoring_tables.list_tables() if t.name == data["table_name"]), None
        )
        version = None
        if table is not None:
            version = next(
                (v for v in uow.scoring_tables.list_versions(table.id)
                 if v.name == data["version_name"]),
                None,
            )  # fmt: skip
        if table is None or version is None or version.is_superseded or table.archived:
            logger.warning("Versão oficial indisponível; nenhuma unidade foi marcada em uso")
            return
        audit = AuditService(SystemClock())
        for acronym in OFFICIAL_TABLE_UNITS:
            unit = units.get(acronym)
            if unit is None or unit.archived or unit.id not in table.unit_ids:
                logger.warning("Unidade %s sem a tabela oficial associada; sem marcação", acronym)
                continue
            if uow.scoring_tables.get_unit_default(unit.id) is not None:
                continue
            if uow.audit.list_for(UNIT_DEFAULT_ENTITY, str(unit.id)):
                continue
            uow.scoring_tables.set_unit_default(unit.id, version.id)
            audit.record(
                uow,
                None,
                UNIT_DEFAULT_ENTITY,
                unit.id,
                AuditAction.CREATE,
                {"version_id": None},
                {"version_id": version.id},
            )
        uow.commit()


def main() -> None:
    from app.core.config import load_settings
    from app.infrastructure.database.session import make_engine, make_session_factory
    from app.infrastructure.security.argon2_hasher import Argon2PasswordHasher

    settings = load_settings()
    engine = make_engine(settings.database_url)
    try:
        seed_reference_data(
            SqlUnitOfWork(make_session_factory(engine)),
            settings.admin_email,
            settings.admin_password.get_secret_value(),
            Argon2PasswordHasher(),
        )
        seed_scoring_tables(SqlUnitOfWork(make_session_factory(engine)))
        seed_unit_defaults(SqlUnitOfWork(make_session_factory(engine)))
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
