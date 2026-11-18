"""GP-D3: the immutability triggers let a DELETE through only inside the process purge (0007)."""

import pytest
from alembic import command
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from tests.integration.conftest import alembic_config
from tests.integration.documents.test_generated_schema import insert_file, insert_generation

PURGE_ON = "SET LOCAL app.process_purge = 'on'"


def _count(engine, table: str) -> int:
    with engine.connect() as conn:
        return conn.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()


@pytest.fixture
def generation(engine, process, base):
    with engine.begin() as conn:
        generation_id = insert_generation(conn, process, base["admin"].id, "TABELA", "PRONTO", 1)
        file_id = insert_file(conn, generation_id)
    return generation_id, file_id


def test_a_direct_delete_still_fails_for_both_tables(engine, generation):
    generation_id, file_id = generation

    with pytest.raises(DBAPIError, match="cannot be deleted"), engine.begin() as conn:
        conn.execute(text("DELETE FROM generated_files WHERE id = :id"), {"id": file_id})
    with pytest.raises(DBAPIError, match="cannot be deleted"), engine.begin() as conn:
        conn.execute(text("DELETE FROM generated_documents WHERE id = :id"), {"id": generation_id})

    assert (_count(engine, "generated_files"), _count(engine, "generated_documents")) == (1, 1)


def test_a_delete_passes_inside_the_purge_transaction(engine, generation):
    generation_id, file_id = generation

    with engine.begin() as conn:
        conn.execute(text(PURGE_ON))
        conn.execute(text("DELETE FROM generated_files WHERE id = :id"), {"id": file_id})
        conn.execute(text("DELETE FROM generated_documents WHERE id = :id"), {"id": generation_id})

    assert (_count(engine, "generated_files"), _count(engine, "generated_documents")) == (0, 0)


def test_the_purge_setting_does_not_outlive_its_transaction(engine, generation):
    _, file_id = generation
    with engine.begin() as conn:
        conn.execute(text(PURGE_ON))
        setting = conn.execute(text("SELECT current_setting('app.process_purge', true)"))
        assert setting.scalar_one() == "on"

    with pytest.raises(DBAPIError, match="cannot be deleted"), engine.begin() as conn:
        conn.execute(text("DELETE FROM generated_files WHERE id = :id"), {"id": file_id})


@pytest.mark.parametrize("value", ["off", "", "ON "])
def test_only_the_value_on_opens_the_delete(engine, generation, value):
    _, file_id = generation

    with pytest.raises(DBAPIError, match="cannot be deleted"), engine.begin() as conn:
        conn.execute(text("SELECT set_config('app.process_purge', :v, true)"), {"v": value})
        conn.execute(text("DELETE FROM generated_files WHERE id = :id"), {"id": file_id})


def test_an_update_stays_blocked_even_inside_the_purge_transaction(engine, generation):
    generation_id, file_id = generation

    with pytest.raises(DBAPIError, match="immutable"), engine.begin() as conn:
        conn.execute(text(PURGE_ON))
        conn.execute(
            text("UPDATE generated_files SET size_bytes = 1 WHERE id = :id"), {"id": file_id}
        )
    with pytest.raises(DBAPIError, match="immutable"), engine.begin() as conn:
        conn.execute(text(PURGE_ON))
        conn.execute(
            text("UPDATE generated_documents SET error_message = 'x' WHERE id = :id"),
            {"id": generation_id},
        )


def test_downgrade_to_0006_restores_the_delete_block_and_upgrade_reopens_the_purge(
    engine, migrated_url, generation
):
    generation_id, file_id = generation
    cfg = alembic_config(migrated_url)
    try:
        command.downgrade(cfg, "0006")
        with pytest.raises(DBAPIError, match="cannot be deleted"), engine.begin() as conn:
            conn.execute(text(PURGE_ON))
            conn.execute(text("DELETE FROM generated_files WHERE id = :id"), {"id": file_id})
        with pytest.raises(DBAPIError, match="cannot be deleted"), engine.begin() as conn:
            conn.execute(text(PURGE_ON))
            conn.execute(
                text("DELETE FROM generated_documents WHERE id = :id"), {"id": generation_id}
            )
    finally:
        command.upgrade(cfg, "head")

    with engine.begin() as conn:
        conn.execute(text(PURGE_ON))
        conn.execute(text("DELETE FROM generated_files WHERE id = :id"), {"id": file_id})
    assert _count(engine, "generated_files") == 0
