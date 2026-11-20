"""DUP-02: activities.merged_into_id and activity_evidences.origin_activity_id
(migration 0008) on real PostgreSQL."""

import uuid

import pytest
from alembic import command
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from tests.integration.conftest import alembic_config
from tests.integration.documents.factories import make_document
from tests.integration.test_scoring_repositories import (  # noqa: F401  (fixture and helpers)
    add_process,
    base,
    make_activity,
)

INDEX = "ix_activities_merged_into"


def _schema(url: str):
    eng = create_engine(url)
    try:
        insp = inspect(eng)
        merged = {c["name"]: c for c in insp.get_columns("activities")}.get("merged_into_id")
        origin = {c["name"]: c for c in insp.get_columns("activity_evidences")}.get(
            "origin_activity_id"
        )
        indexes = {i["name"]: i for i in insp.get_indexes("activities")}
        return merged, origin, indexes.get(INDEX)
    finally:
        eng.dispose()


def _index_predicate(engine) -> str:
    with engine.connect() as conn:
        return conn.execute(
            text("SELECT indexdef FROM pg_indexes WHERE indexname = :n"), {"n": INDEX}
        ).scalar_one()


def test_upgrade_adds_both_nullable_uuid_columns_and_the_partial_index(migrated_url, engine):
    merged, origin, index = _schema(migrated_url)

    assert merged is not None and merged["nullable"] is True
    assert origin is not None and origin["nullable"] is True
    assert index is not None and index["column_names"] == ["merged_into_id"]
    assert "WHERE (merged_into_id IS NOT NULL)" in _index_predicate(engine)


def test_downgrade_one_revision_drops_both_columns_and_the_index(migrated_url):
    cfg = alembic_config(migrated_url)
    try:
        command.downgrade(cfg, "0007")
        assert _schema(migrated_url) == (None, None, None)
    finally:
        command.upgrade(cfg, "head")

    merged, origin, index = _schema(migrated_url)
    assert merged is not None and origin is not None and index is not None


def test_existing_activities_keep_their_data_and_have_no_merge_marks(
    uow_factory, base, engine  # noqa: F811
):
    process = add_process(uow_factory, base)
    activity = make_activity(process, base, candidates=())
    with uow_factory() as uow:
        uow.activities.add(activity)
        uow.commit()

    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT title, merged_into_id FROM activities WHERE id = :i"),
            {"i": activity.id},
        ).one()
    assert (row.title, row.merged_into_id) == ("Aula de Cálculo", None)


def test_merged_into_id_accepts_an_existing_activity_and_refuses_an_unknown_id(
    uow_factory, base, engine  # noqa: F811
):
    process = add_process(uow_factory, base)
    kept = make_activity(process, base, title="Mantida", candidates=())
    other = make_activity(process, base, title="Outra", candidates=())
    with uow_factory() as uow:
        uow.activities.add(kept)
        uow.activities.add(other)
        uow.commit()

    with engine.begin() as conn:
        conn.execute(
            text("UPDATE activities SET merged_into_id = :k WHERE id = :o"),
            {"k": kept.id, "o": other.id},
        )
    with pytest.raises(IntegrityError), engine.begin() as conn:
        conn.execute(
            text("UPDATE activities SET merged_into_id = :x WHERE id = :o"),
            {"x": uuid.uuid4(), "o": kept.id},
        )


def test_origin_activity_id_accepts_an_existing_activity_and_refuses_an_unknown_one(
    uow_factory, base, engine  # noqa: F811
):
    process = add_process(uow_factory, base)
    activity = make_activity(process, base, candidates=())
    document = make_document(process, base["admin"].id)
    with uow_factory() as uow:
        uow.activities.add(activity)
        uow.documents.add(document)
        uow.commit()

    insert = text(
        "INSERT INTO activity_evidences (id, activity_id, document_id, page_number, excerpt, "
        "created_by, origin_activity_id) VALUES (:i, :a, :d, :p, 'x', :u, :o)"
    )

    def params(page, origin):
        return {"i": uuid.uuid4(), "a": activity.id, "d": document.id, "p": page,
                "u": base["admin"].id, "o": origin}  # fmt: skip

    with engine.begin() as conn:
        conn.execute(insert, params(1, activity.id))
    with pytest.raises(IntegrityError), engine.begin() as conn:
        conn.execute(insert, params(2, uuid.uuid4()))
