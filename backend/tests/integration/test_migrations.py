"""INFRA-02 / AUD-02: initial schema migration on real PostgreSQL."""

import uuid
from datetime import UTC, datetime

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.infrastructure.database.models import Base
from tests.integration.conftest import alembic_config

TABLES = {
    "users",
    "user_units",
    "sessions",
    "login_attempts",
    "academic_units",
    "career_structures",
    "career_versions",
    "professors",
    "functional_processes",
    "audit_logs",
    "scoring_tables",
    "scoring_table_units",
    "scoring_table_versions",
    "scoring_groups",
    "scoring_criteria",
    "activities",
    "activity_candidates",
    "documents",
    "extraction_runs",
    "document_pages",
    "processing_jobs",
    "activity_evidences",
    "generated_documents",
    "generated_files",
    "report_wording_jobs",
    "report_drafts",
    "comprovante_layouts",
    "norms",
    "board_ordinances",
    "board_opinions",
    "request_settings",
    "dossier_deliveries",
}


def _tables(url: str) -> set[str]:
    eng = create_engine(url)
    try:
        return set(inspect(eng).get_table_names()) - {"alembic_version"}
    finally:
        eng.dispose()


def test_upgrade_head_and_downgrade_base(migrated_url):
    cfg = alembic_config(migrated_url)
    assert _tables(migrated_url) == TABLES

    command.downgrade(cfg, "base")
    assert _tables(migrated_url) == set()

    command.upgrade(cfg, "head")
    assert _tables(migrated_url) == TABLES


def test_models_match_migrated_schema(engine):
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    assert diff == []


def _insert_audit(conn) -> int:
    return conn.execute(
        text(
            "INSERT INTO audit_logs (occurred_at, entity, entity_id, action, changes) "
            "VALUES (:at, 'professor', :eid, 'CREATE', '{}') RETURNING id"
        ),
        {"at": datetime.now(UTC), "eid": str(uuid.uuid4())},
    ).scalar_one()


def test_audit_logs_accept_insert(engine):
    with engine.begin() as conn:
        audit_id = _insert_audit(conn)
    with engine.connect() as conn:
        count = conn.execute(
            text("SELECT count(*) FROM audit_logs WHERE id = :id"), {"id": audit_id}
        ).scalar_one()
    assert count == 1


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE audit_logs SET justification = 'x' WHERE id = :id",
        "DELETE FROM audit_logs WHERE id = :id",
    ],
)
def test_audit_logs_reject_update_and_delete(engine, statement):
    with engine.begin() as conn:
        audit_id = _insert_audit(conn)

    with pytest.raises(DBAPIError, match="append-only"), engine.begin() as conn:
        conn.execute(text(statement), {"id": audit_id})

    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT justification FROM audit_logs WHERE id = :id"), {"id": audit_id}
        ).one()
    assert row.justification is None


def test_user_email_is_unique_case_insensitively(engine):
    insert = text(
        "INSERT INTO users (id, email, name, role, password_hash, active) "
        "VALUES (:id, :email, 'X', 'ADMIN', 'h', true)"
    )
    with engine.begin() as conn:
        conn.execute(insert, {"id": uuid.uuid4(), "email": "admin@ufpa.br"})
    with pytest.raises(IntegrityError), engine.begin() as conn:
        conn.execute(insert, {"id": uuid.uuid4(), "email": "ADMIN@ufpa.br"})
