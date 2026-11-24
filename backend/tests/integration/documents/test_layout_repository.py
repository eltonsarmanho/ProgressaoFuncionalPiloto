"""ARR-07: the Comprovante layout repository on real PostgreSQL (optimistic lock by version)."""

import dataclasses

import pytest

from app.domain.errors import Conflict, NotFound, StaleVersion
from app.infrastructure.database.repositories import SqlLayoutRepository
from tests.integration.documents.generated_support import make_layout


def call(session_factory, action):
    """Runs `action(repository)` in its own session and commits."""
    with session_factory() as session:
        result = action(SqlLayoutRepository(session))
        session.commit()
    return result


def get(session_factory, process_id):
    with session_factory() as session:
        return SqlLayoutRepository(session).get(process_id)


def test_a_process_without_a_saved_layout_has_none(session_factory, process):
    assert get(session_factory, process.id) is None


def test_the_first_save_expects_version_0_and_stores_version_1_with_every_field(
    session_factory, process, base
):
    layout = make_layout(process)

    created = call(session_factory, lambda r: r.create(layout, base["admin"].id, 0))

    expected = dataclasses.replace(layout, version=1)
    assert created == expected
    assert get(session_factory, process.id) == expected


def test_a_first_save_with_a_version_other_than_0_is_stale_and_stores_nothing(
    session_factory, process, base
):
    with pytest.raises(StaleVersion):
        call(session_factory, lambda r: r.create(make_layout(process), base["admin"].id, 2))

    assert get(session_factory, process.id) is None


def test_a_second_create_for_the_same_process_conflicts(session_factory, process, base):
    call(session_factory, lambda r: r.create(make_layout(process), base["admin"].id, 0))

    with pytest.raises(Conflict):
        call(session_factory, lambda r: r.create(make_layout(process), base["admin"].id, 0))


def test_update_replaces_the_content_and_raises_the_version(session_factory, process, base):
    first = make_layout(process)
    call(session_factory, lambda r: r.create(first, base["admin"].id, 0))
    reordered = dataclasses.replace(first, activities=first.activities[::-1])

    result = call(session_factory, lambda r: r.update(reordered, base["admin"].id, 1))

    assert result == dataclasses.replace(reordered, version=2)
    assert get(session_factory, process.id) == dataclasses.replace(reordered, version=2)


def test_update_with_a_stale_version_raises_and_does_not_overwrite(session_factory, process, base):
    first = make_layout(process)
    call(session_factory, lambda r: r.create(first, base["admin"].id, 0))
    second = make_layout(process)
    call(session_factory, lambda r: r.update(second, base["admin"].id, 1))

    with pytest.raises(StaleVersion):
        call(session_factory, lambda r: r.update(make_layout(process), base["admin"].id, 1))

    assert get(session_factory, process.id) == dataclasses.replace(second, version=2)


def test_update_of_a_process_without_a_layout_is_not_found(session_factory, process, base):
    with pytest.raises(NotFound):
        call(session_factory, lambda r: r.update(make_layout(process), base["admin"].id, 1))
