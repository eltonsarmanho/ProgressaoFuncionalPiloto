"""Idempotent reference data seed (CARR-02, UNIT-03, initial ADMIN).

Run with: python -m app.infrastructure.database.seed
"""

import json
import uuid
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from app.domain.entities.academic_unit import AcademicUnit, UnitKind
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
from app.infrastructure.database.repositories import SqlUnitOfWork

STRUCTURE_CODE = "MAGISTERIO_SUPERIOR"
STRUCTURE_NAME = "Magistério Superior"

CAMPUS = ("Campus Universitário do Tocantins/Cametá", "CUNTINS", UnitKind.CAMPUS)
FASI = ("Faculdade de Sistemas de Informação", "FASI", UnitKind.FACULDADE)
IFCH = ("Instituto de Filosofia e Ciências Humanas", "IFCH", UnitKind.INSTITUTO)

SEED_DATA = Path(__file__).parent / "seed_data"
OFFICIAL_TABLE_SEED = "ufpa.json"
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

    OFI-01, OFI-08..OFI-11. Idempotent: an existing table keeps its units; an existing
    version is left untouched. Requires the units created by `seed_reference_data`.
    """
    with uow:
        units = {u.acronym: u for u in uow.units.list()}
        missing = [a for a in OFFICIAL_TABLE_UNITS if a not in units]
        if missing:
            raise LookupError(f"Unidade {missing[0]} não cadastrada; rode a semente de unidades")
        data = json.loads((SEED_DATA / OFFICIAL_TABLE_SEED).read_text(encoding="utf-8"))
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
        _archive_legacy_tables(uow)
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
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
