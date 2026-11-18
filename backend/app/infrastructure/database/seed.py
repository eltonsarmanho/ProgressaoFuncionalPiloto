"""Idempotent reference data seed (CARR-02, UNIT-03, initial ADMIN).

Run with: python -m app.infrastructure.database.seed
"""

import uuid

from app.domain.entities.academic_unit import AcademicUnit, UnitKind
from app.domain.entities.user import Role, User
from app.domain.repositories.ports import PasswordHasher
from app.domain.rules.career_catalog import MAGISTERIO_SUPERIOR_VERSIONS
from app.infrastructure.database.repositories import SqlUnitOfWork

STRUCTURE_CODE = "MAGISTERIO_SUPERIOR"
STRUCTURE_NAME = "Magistério Superior"

CAMPUS = ("Campus Universitário do Tocantins/Cametá", "CUNTINS", UnitKind.CAMPUS)
FASI = ("Faculdade de Sistemas de Informação", "FASI", UnitKind.FACULDADE)
IFCH = ("Instituto de Filosofia e Ciências Humanas", "IFCH", UnitKind.INSTITUTO)


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
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
