"""NBASE-01 / NLINK-01: migration 0010 (norms table and norm_code columns) on real PostgreSQL."""

import uuid
from datetime import date

import pytest
from alembic import command
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from tests.integration.conftest import alembic_config

_INSERT_NORM = text(
    "INSERT INTO norms (id, code, title, kind, issuer, published_on, valid_from, valid_to) "
    "VALUES (:id, :code, 'Norma sintética', 'LEI', 'Órgão sintético', :published, :vf, :vt)"
)


def _norm(code: str = "NORMA-SINTETICA", vf: date | None = None, vt: date | None = None) -> dict:
    return {
        "id": uuid.uuid4(),
        "code": code,
        "published": date(2020, 1, 1),
        "vf": vf,
        "vt": vt,
    }


def _schema(url: str) -> dict:
    eng = create_engine(url)
    try:
        insp = inspect(eng)
        with eng.connect() as conn:
            enum_exists = bool(
                conn.execute(text("SELECT 1 FROM pg_type WHERE typname = 'norm_kind'")).first()
            )
        norm_code = {}
        for table in ("career_versions", "scoring_table_versions"):
            norm_code[table] = {c["name"]: c for c in insp.get_columns(table)}.get("norm_code")
        return {
            "tables": set(insp.get_table_names()),
            "enum": enum_exists,
            "norm_code": norm_code,
            "columns": {c["name"]: c for c in insp.get_columns("norms")}
            if "norms" in insp.get_table_names()
            else {},
            "foreign_keys": {
                table: insp.get_foreign_keys(table)
                for table in ("career_versions", "scoring_table_versions")
            },
        }
    finally:
        eng.dispose()


def test_upgrade_creates_the_norms_table_with_its_columns_and_the_kind_enum(migrated_url):
    schema = _schema(migrated_url)

    assert "norms" in schema["tables"]
    assert schema["enum"] is True
    columns = schema["columns"]
    assert set(columns) == {
        "id", "code", "title", "kind", "issuer", "published_on", "valid_from", "valid_to",
        "source_url", "file_internal_name", "file_original_name", "file_size_bytes",
        "file_sha256", "notes", "archived", "version", "created_at",
    }
    required = {"id", "code", "title", "kind", "issuer", "published_on", "archived", "version",
                "created_at"}
    assert {name for name, c in columns.items() if not c["nullable"]} == required


def test_career_versions_and_scoring_table_versions_get_a_nullable_norm_code_without_a_key(
    migrated_url,
):
    schema = _schema(migrated_url)

    for table in ("career_versions", "scoring_table_versions"):
        column = schema["norm_code"][table]
        assert column is not None and column["nullable"] is True
        assert column["type"].length == 50
        # design: no foreign key from norm_code to norms.code
        assert not [
            fk for fk in schema["foreign_keys"][table] if fk["constrained_columns"] == ["norm_code"]
        ]


def test_two_norms_with_the_same_code_are_refused(engine):
    with engine.begin() as conn:
        conn.execute(_INSERT_NORM, _norm("LEI-REPETIDA"))

    with pytest.raises(IntegrityError), engine.begin() as conn:
        conn.execute(_INSERT_NORM, _norm("LEI-REPETIDA"))


def test_a_norm_that_ends_before_it_starts_is_refused(engine):
    with pytest.raises(IntegrityError), engine.begin() as conn:
        conn.execute(_INSERT_NORM, _norm(vf=date(2025, 1, 2), vt=date(2025, 1, 1)))


def test_a_norm_that_ends_the_day_it_starts_or_has_only_one_bound_is_accepted(engine):
    with engine.begin() as conn:
        conn.execute(_INSERT_NORM, _norm("IGUAL", vf=date(2025, 1, 1), vt=date(2025, 1, 1)))
        conn.execute(_INSERT_NORM, _norm("SO-INICIO", vf=date(2025, 1, 1)))
        conn.execute(_INSERT_NORM, _norm("SO-FIM", vt=date(2025, 1, 1)))
        conn.execute(_INSERT_NORM, _norm("SEM-VIGENCIA"))

    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT archived, version FROM norms WHERE code = 'SEM-VIGENCIA'")
        ).one()
    assert (row.archived, row.version) == (False, 1)


def test_downgrade_removes_the_table_the_enum_and_the_columns_and_keeps_existing_versions(
    migrated_url, engine  # noqa: ARG001  (engine makes the autouse cleanup truncate the rows)
):
    cfg = alembic_config(migrated_url)
    structure_id, table_id, career_id, scoring_id = (uuid.uuid4() for _ in range(4))
    eng = create_engine(migrated_url)
    try:
        command.downgrade(cfg, "0009")
        schema = _schema(migrated_url)
        assert "norms" not in schema["tables"]
        assert schema["enum"] is False
        assert schema["norm_code"] == {"career_versions": None, "scoring_table_versions": None}

        # Rows that exist before the upgrade keep working and get a null norm_code.
        with eng.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO career_structures (id, code, name) VALUES (:i, 'EST', 'Est')"
                ),
                {"i": structure_id},
            )
            conn.execute(
                text(
                    "INSERT INTO career_versions (id, structure_id, name, norm_reference, "
                    "definition) VALUES (:i, :s, 'Versão', 'ref', '{}'::jsonb)"
                ),
                {"i": career_id, "s": structure_id},
            )
            conn.execute(
                text(
                    "INSERT INTO scoring_tables (id, name, archived) VALUES (:i, 'Tabela', false)"
                ),
                {"i": table_id},
            )
            conn.execute(
                text(
                    "INSERT INTO scoring_table_versions (id, table_id, name, valid_from, "
                    "norm_reference, status) VALUES (:i, :t, 'V1', '2020-01-01', 'ref', 'OFICIAL')"
                ),
                {"i": scoring_id, "t": table_id},
            )

        command.upgrade(cfg, "head")

        schema = _schema(migrated_url)
        assert "norms" in schema["tables"] and schema["enum"] is True
        with eng.connect() as conn:
            career_code = conn.execute(
                text("SELECT norm_code FROM career_versions WHERE id = :i"), {"i": career_id}
            ).scalar_one()
            scoring_code = conn.execute(
                text("SELECT norm_code FROM scoring_table_versions WHERE id = :i"),
                {"i": scoring_id},
            ).scalar_one()
        assert (career_code, scoring_code) == (None, None)
    finally:
        eng.dispose()
        command.upgrade(cfg, "head")
