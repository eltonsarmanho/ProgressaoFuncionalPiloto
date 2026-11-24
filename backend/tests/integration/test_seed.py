"""CARR-02 / UNIT-03: idempotent reference data seed."""

from sqlalchemy import text

from app.domain.entities.academic_unit import UnitKind
from app.domain.entities.professor import Titration
from app.domain.entities.user import Role
from app.domain.rules.career_catalog import MAGISTERIO_SUPERIOR_VERSIONS
from app.infrastructure.database import seed
from app.infrastructure.database.seed import seed_reference_data

ADMIN_EMAIL = "admin@ufpa.br"


class FakeHasher:
    def hash(self, password: str) -> str:
        return f"hashed:{password}"

    def verify(self, password_hash: str, password: str) -> bool:
        return password_hash == f"hashed:{password}"


def _counts(engine) -> dict[str, int]:
    tables = ("career_structures", "career_versions", "academic_units", "users")
    with engine.connect() as conn:
        return {t: conn.execute(text(f"SELECT count(*) FROM {t}")).scalar_one() for t in tables}


def test_seed_twice_does_not_duplicate_records(engine, uow_factory):
    seed_reference_data(uow_factory(), ADMIN_EMAIL, "first-password", FakeHasher())
    first = _counts(engine)
    seed_reference_data(uow_factory(), ADMIN_EMAIL, "other-password", FakeHasher())

    assert first == {
        "career_structures": 1,
        "career_versions": 2,
        "academic_units": 3,
        "users": 1,
    }
    assert _counts(engine) == first


def test_seeded_versions_are_identical_to_catalog(uow_factory):
    seed_reference_data(uow_factory(), ADMIN_EMAIL, "first-password", FakeHasher())

    with uow_factory() as uow:
        versions = tuple(uow.career_versions.list_versions(seed.STRUCTURE_CODE))

    assert versions == MAGISTERIO_SUPERIOR_VERSIONS
    assert [v.name for v in versions] == [
        "Res. 4.644/2015-CONSEPE",
        "Lei 12.772/2012 com redação da Lei 15.141/2025",
    ]
    assert all(v.norm_reference for v in versions)
    # NLINK-02, NTIT-06: the norm links and the titration rules of the catalog survive the database
    assert [v.norm_code for v in versions] == ["RES-4644-2015-CONSEPE", "LEI-12772-2012"]
    assert [v.required_titration_norm_code for v in versions] == [None, "MANUAL-PROGEP-PROGRESSAO"]
    assert [
        [c.required_titration for c in v.classes] for v in versions
    ] == [
        [None] * 5,
        [None, None, Titration.DOUTORADO, Titration.DOUTORADO],
    ]


def test_seeded_units(uow_factory):
    seed_reference_data(uow_factory(), ADMIN_EMAIL, "first-password", FakeHasher())

    with uow_factory() as uow:
        units = {u.acronym: u for u in uow.units.list()}

    assert set(units) == {"CUNTINS", "FASI", "IFCH"}
    campus, fasi, ifch = units["CUNTINS"], units["FASI"], units["IFCH"]
    assert (campus.name, campus.kind) == (
        "Campus Universitário do Tocantins/Cametá",
        UnitKind.CAMPUS,
    )
    assert (fasi.name, fasi.kind, fasi.parent_id) == (
        "Faculdade de Sistemas de Informação",
        UnitKind.FACULDADE,
        campus.id,
    )
    assert (ifch.name, ifch.kind) == (
        "Instituto de Filosofia e Ciências Humanas",
        UnitKind.INSTITUTO,
    )
    assert not any(u.archived for u in units.values())


def test_seeded_admin_keeps_original_password_on_rerun(uow_factory):
    seed_reference_data(uow_factory(), ADMIN_EMAIL, "first-password", FakeHasher())
    seed_reference_data(uow_factory(), ADMIN_EMAIL, "other-password", FakeHasher())

    with uow_factory() as uow:
        admin = uow.users.get_by_email(ADMIN_EMAIL)

    assert admin.role is Role.ADMIN
    assert admin.active is True
    assert admin.password_hash == "hashed:first-password"


def test_main_seeds_admin_with_argon2id_hash(migrated_url, uow_factory, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", migrated_url)
    monkeypatch.setenv("ADMIN_EMAIL", ADMIN_EMAIL)
    monkeypatch.setenv("ADMIN_PASSWORD", "admin-password-123")

    seed.main()

    with uow_factory() as uow:
        admin = uow.users.get_by_email(ADMIN_EMAIL)
    assert admin.password_hash.startswith("$argon2id$")
    assert "admin-password-123" not in admin.password_hash
