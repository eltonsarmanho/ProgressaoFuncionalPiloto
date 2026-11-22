"""DOS-04: the "Entregue" marks of the dossier checklist on real PostgreSQL."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import text

from app.infrastructure.database.repositories import SqlDossierDeliveryRepository

NOW = datetime(2026, 11, 22, 10, 0, tzinfo=UTC)


def call(session_factory, action):
    with session_factory() as session:
        result = action(SqlDossierDeliveryRepository(session))
        session.commit()
    return result


def rows(engine):
    with engine.connect() as conn:
        return conn.execute(
            text("SELECT process_id, item_key, marked_by, marked_at FROM dossier_deliveries")
        ).all()


def test_marking_stores_the_mark_and_reports_the_change(session_factory, process, base):
    changed = call(
        session_factory, lambda r: r.mark(process.id, "CURRICULO_LATTES", base["admin"].id, NOW)
    )

    assert changed is True
    assert call(session_factory, lambda r: r.keys(process.id)) == {"CURRICULO_LATTES"}


def test_marking_again_changes_nothing_and_does_not_duplicate(
    session_factory, process, base, engine
):
    admin = base["admin"].id
    call(session_factory, lambda r: r.mark(process.id, "CURRICULO_LATTES", admin, NOW))

    again = call(
        session_factory,
        lambda r: r.mark(process.id, "CURRICULO_LATTES", admin, NOW + timedelta(hours=1)),
    )

    assert again is False
    assert len(rows(engine)) == 1
    assert rows(engine)[0].marked_at == NOW  # the first mark stays


def test_the_keys_of_a_process_without_marks_are_empty(session_factory, process):
    assert call(session_factory, lambda r: r.keys(process.id)) == set()


def test_keys_lists_only_the_keys_of_the_process(session_factory, process, other_process, base):
    admin = base["admin"].id
    call(session_factory, lambda r: r.mark(process.id, "CURRICULO_LATTES", admin, NOW))
    call(session_factory, lambda r: r.mark(process.id, "PORTARIA_ULTIMA_PROGRESSAO", admin, NOW))
    call(
        session_factory,
        lambda r: r.mark(other_process.id, "DECLARACAO_EXERCICIOS_ANTERIORES", admin, NOW),
    )

    assert call(session_factory, lambda r: r.keys(process.id)) == {
        "CURRICULO_LATTES",
        "PORTARIA_ULTIMA_PROGRESSAO",
    }
    assert call(session_factory, lambda r: r.keys(other_process.id)) == {
        "DECLARACAO_EXERCICIOS_ANTERIORES"
    }


def test_unmarking_removes_the_mark_and_a_second_unmark_changes_nothing(
    session_factory, process, base
):
    call(session_factory, lambda r: r.mark(process.id, "CURRICULO_LATTES", base["admin"].id, NOW))

    first = call(session_factory, lambda r: r.unmark(process.id, "CURRICULO_LATTES"))
    second = call(session_factory, lambda r: r.unmark(process.id, "CURRICULO_LATTES"))

    assert (first, second) == (True, False)
    assert call(session_factory, lambda r: r.keys(process.id)) == set()


def test_unmarking_does_not_touch_the_marks_of_another_process(
    session_factory, process, other_process, base
):
    admin = base["admin"].id
    call(session_factory, lambda r: r.mark(process.id, "CURRICULO_LATTES", admin, NOW))
    call(session_factory, lambda r: r.mark(other_process.id, "CURRICULO_LATTES", admin, NOW))

    call(session_factory, lambda r: r.unmark(process.id, "CURRICULO_LATTES"))

    assert call(session_factory, lambda r: r.keys(other_process.id)) == {"CURRICULO_LATTES"}


def test_who_marked_and_when_stay_recorded(session_factory, process, base, engine):
    admin = base["admin"].id
    call(session_factory, lambda r: r.mark(process.id, "CURRICULO_LATTES", admin, NOW))

    row = rows(engine)[0]

    assert (row.process_id, row.item_key, row.marked_by, row.marked_at) == (
        process.id,
        "CURRICULO_LATTES",
        admin,
        NOW,
    )
