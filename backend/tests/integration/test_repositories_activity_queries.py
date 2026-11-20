"""SEC-01: the candidates of the activities of a process are loaded in one query."""

from dataclasses import replace

import pytest
from sqlalchemy import event

from app.domain.entities.activity import Candidate
from tests.integration.test_scoring_repositories import (  # noqa: F401  (fixture and helpers)
    add_process,
    base,
    make_activity,
)


@pytest.fixture
def process(uow_factory, base):  # noqa: F811
    return add_process(uow_factory, base)


def _add_many(uow_factory, process, base, count):  # noqa: F811
    activities = [
        make_activity(
            process,
            base,
            title=f"Atividade {n}",
            candidates=(Candidate(2, 3, f"a{n}"), Candidate(1, 2, f"b{n}")),
        )
        for n in range(count)
    ]
    with uow_factory() as uow:
        for activity in activities:
            uow.activities.add(activity)
        uow.commit()
    return activities


def _count_selects(engine, call) -> int:
    seen: list[str] = []

    def record(conn, cursor, statement, *args):
        seen.append(statement)

    event.listen(engine, "before_cursor_execute", record)
    try:
        call()
    finally:
        event.remove(engine, "before_cursor_execute", record)
    return len(seen)


def test_listing_300_activities_runs_as_many_queries_as_listing_5(
    uow_factory, engine, base, process  # noqa: F811
):
    _add_many(uow_factory, process, base, 5)

    def list_all():
        with uow_factory() as uow:
            return uow.activities.list_for_process(process.id)

    queries_with_few = _count_selects(engine, list_all)
    _add_many(uow_factory, process, base, 295)

    queries_with_many = _count_selects(engine, list_all)

    assert len(list_all()) == 300
    assert queries_with_many == queries_with_few
    assert queries_with_many == 2  # the activities and, in one query, all their candidates


def test_the_candidates_keep_their_order_and_stay_with_their_activity(
    uow_factory, base, process  # noqa: F811
):
    activities = _add_many(uow_factory, process, base, 4)

    with uow_factory() as uow:
        listed = {a.id: a for a in uow.activities.list_for_process(process.id)}

    for activity in activities:
        assert listed[activity.id].candidates == (
            Candidate(1, 2, activity.candidates[1].justification),
            Candidate(2, 3, activity.candidates[0].justification),
        )


def test_the_activities_merged_into_one_are_listed_with_their_candidates_too(
    uow_factory, engine, base, process  # noqa: F811
):
    kept, *others = _add_many(uow_factory, process, base, 6)
    with uow_factory() as uow:
        for other in others:
            uow.activities.set_merged_into(replace(other), kept.id, other.version)
        uow.commit()

    def merged_into_kept():
        with uow_factory() as uow:
            return uow.activities.list_merged_into(kept.id)

    queries = _count_selects(engine, merged_into_kept)

    found = merged_into_kept()
    assert {a.title for a in found} == {a.title for a in others}
    assert all(len(a.candidates) == 2 for a in found)
    assert queries == 2
