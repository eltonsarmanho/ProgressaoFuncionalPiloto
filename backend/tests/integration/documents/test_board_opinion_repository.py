"""PAR-01, PAR-12, PAR-13, REQ-05, PORT-12: the opinion and request settings repositories on real
PostgreSQL."""

import dataclasses
from datetime import date

import pytest

from app.domain.entities.board import BoardOpinion, OpinionConclusion, RequestSettings
from app.domain.errors import Conflict, StaleVersion
from app.infrastructure.database.repositories import (
    SqlOpinionRepository,
    SqlRequestSettingsRepository,
)


def opinion_call(session_factory, action):
    with session_factory() as session:
        result = action(SqlOpinionRepository(session))
        session.commit()
    return result


def settings_call(session_factory, action):
    with session_factory() as session:
        result = action(SqlRequestSettingsRepository(session))
        session.commit()
    return result


def make_opinion(process, **changes) -> BoardOpinion:
    data = {
        "process_id": process.id,
        "conclusion": OpinionConclusion.FAVORAVEL,
        "opinion_date": date(2025, 4, 2),
        "place": "Belém",
        "notes": "Observação da banca.",
    }
    data.update(changes)
    return BoardOpinion(**data)


# --- opinion --------------------------------------------------------------------------------


def test_an_opinion_not_saved_yet_is_none(session_factory, process):
    assert opinion_call(session_factory, lambda r: r.get(process.id)) is None


def test_the_first_save_stores_the_opinion_with_version_1(session_factory, process, base):
    opinion = make_opinion(process)

    created = opinion_call(session_factory, lambda r: r.create(opinion, base["admin"].id, 0))

    expected = dataclasses.replace(opinion, version=1)
    assert created == expected
    assert opinion_call(session_factory, lambda r: r.get(process.id)) == expected


def test_nobody_chose_the_conclusion_so_it_is_stored_as_none(session_factory, process, base):
    opinion = BoardOpinion(process_id=process.id, place="Belém")

    opinion_call(session_factory, lambda r: r.create(opinion, base["admin"].id, 0))

    stored = opinion_call(session_factory, lambda r: r.get(process.id))
    assert stored.conclusion is None
    assert stored.place == "Belém"


def test_create_with_a_version_other_than_0_is_stale_and_stores_nothing(
    session_factory, process, base
):
    with pytest.raises(StaleVersion):
        opinion_call(
            session_factory, lambda r: r.create(make_opinion(process), base["admin"].id, 2)
        )

    assert opinion_call(session_factory, lambda r: r.get(process.id)) is None


def test_a_second_create_conflicts(session_factory, process, base):
    opinion_call(session_factory, lambda r: r.create(make_opinion(process), base["admin"].id, 0))

    with pytest.raises(Conflict) as error:
        opinion_call(
            session_factory, lambda r: r.create(make_opinion(process), base["admin"].id, 0)
        )

    assert not isinstance(error.value, StaleVersion)


def test_update_with_the_right_version_stores_the_changes_and_goes_to_version_2(
    session_factory, process, base
):
    admin = base["admin"].id
    opinion_call(session_factory, lambda r: r.create(make_opinion(process), admin, 0))
    changed = make_opinion(
        process,
        conclusion=OpinionConclusion.DESFAVORAVEL,
        opinion_date=date(2025, 5, 1),
        place="Santarém",
        notes="Outra observação.",
    )

    updated = opinion_call(session_factory, lambda r: r.update(changed, admin, 1))

    expected = dataclasses.replace(changed, version=2)
    assert updated == expected
    assert opinion_call(session_factory, lambda r: r.get(process.id)) == expected


def test_update_from_an_old_version_is_stale_and_keeps_what_was_stored(
    session_factory, process, base
):
    admin = base["admin"].id
    opinion_call(session_factory, lambda r: r.create(make_opinion(process), admin, 0))
    opinion_call(session_factory, lambda r: r.update(make_opinion(process, place="A"), admin, 1))

    with pytest.raises(StaleVersion):
        opinion_call(
            session_factory, lambda r: r.update(make_opinion(process, place="B"), admin, 1)
        )

    stored = opinion_call(session_factory, lambda r: r.get(process.id))
    assert (stored.place, stored.version) == ("A", 2)


def test_notes_of_5000_characters_come_back_whole(session_factory, process, base):
    notes = "x" * 4999 + "y"

    opinion_call(
        session_factory,
        lambda r: r.create(make_opinion(process, notes=notes), base["admin"].id, 0),
    )

    assert opinion_call(session_factory, lambda r: r.get(process.id)).notes == notes


def test_the_conclusion_can_go_back_to_none(session_factory, process, base):
    admin = base["admin"].id
    opinion_call(session_factory, lambda r: r.create(make_opinion(process), admin, 0))

    opinion_call(
        session_factory, lambda r: r.update(make_opinion(process, conclusion=None), admin, 1)
    )

    assert opinion_call(session_factory, lambda r: r.get(process.id)).conclusion is None


def test_the_opinions_of_two_processes_are_independent(
    session_factory, process, other_process, base
):
    admin = base["admin"].id
    opinion_call(session_factory, lambda r: r.create(make_opinion(process, place="A"), admin, 0))
    opinion_call(
        session_factory, lambda r: r.create(make_opinion(other_process, place="B"), admin, 0)
    )

    assert opinion_call(session_factory, lambda r: r.get(process.id)).place == "A"
    assert opinion_call(session_factory, lambda r: r.get(other_process.id)).place == "B"


# --- request settings (the city) ------------------------------------------------------------


def test_the_city_not_saved_yet_is_none(session_factory, process):
    assert settings_call(session_factory, lambda r: r.get(process.id)) is None


def test_the_first_save_of_the_city_stores_version_1(session_factory, process):
    settings = RequestSettings(process.id, "Belém")

    created = settings_call(session_factory, lambda r: r.create(settings, 0))

    expected = dataclasses.replace(settings, version=1)
    assert created == expected
    assert settings_call(session_factory, lambda r: r.get(process.id)) == expected


def test_a_city_of_100_characters_comes_back_whole(session_factory, process):
    city = "c" * 100

    settings_call(session_factory, lambda r: r.create(RequestSettings(process.id, city), 0))

    assert settings_call(session_factory, lambda r: r.get(process.id)).city == city


def test_create_of_the_city_with_a_version_other_than_0_is_stale_and_a_second_one_conflicts(
    session_factory, process
):
    with pytest.raises(StaleVersion):
        settings_call(session_factory, lambda r: r.create(RequestSettings(process.id, "A"), 4))
    assert settings_call(session_factory, lambda r: r.get(process.id)) is None

    settings_call(session_factory, lambda r: r.create(RequestSettings(process.id, "A"), 0))
    with pytest.raises(Conflict) as error:
        settings_call(session_factory, lambda r: r.create(RequestSettings(process.id, "B"), 0))
    assert not isinstance(error.value, StaleVersion)


def test_the_city_update_checks_the_version_and_can_clear_the_city(session_factory, process):
    settings_call(session_factory, lambda r: r.create(RequestSettings(process.id, "Belém"), 0))

    updated = settings_call(
        session_factory, lambda r: r.update(RequestSettings(process.id, "Santarém"), 1)
    )
    assert (updated.city, updated.version) == ("Santarém", 2)

    with pytest.raises(StaleVersion):
        settings_call(session_factory, lambda r: r.update(RequestSettings(process.id, "X"), 1))
    assert settings_call(session_factory, lambda r: r.get(process.id)).city == "Santarém"

    settings_call(session_factory, lambda r: r.update(RequestSettings(process.id, None), 2))
    assert settings_call(session_factory, lambda r: r.get(process.id)).city is None
