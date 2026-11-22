"""PAR-01, PAR-12, PAR-13, REQ-05, BNAV-02, BNAV-03: SaveOpinion and SaveRequestSettings."""

import json
from datetime import date

import pytest

from app.domain.entities.audit import AuditAction
from app.domain.entities.board import OpinionConclusion
from app.domain.entities.process import ProcessStatus
from app.domain.errors import Conflict, NotFound, StaleVersion, ValidationFailed
from tests.integration.doc_usecases.board_support import save_opinion_uc, save_settings_uc
from tests.integration.doc_usecases.draft_support import set_status

DAY = date(2025, 4, 1)


def opinion(world, conclusion=None, when=None, place=None, notes=None, version=0, actor=None):
    return save_opinion_uc(world).execute(
        actor or world.docente, world.process.id, conclusion, when, place, notes, version
    )


def city(world, text="Belém", version=0, actor=None):
    return save_settings_uc(world).execute(
        actor or world.docente, world.process.id, text, version
    )


def stored_opinion(world):
    with world.uow_factory() as uow:
        return uow.opinions.get(world.process.id)


def stored_city(world):
    with world.uow_factory() as uow:
        return uow.request_settings.get(world.process.id)


def events(world, entity):
    with world.uow_factory() as uow:
        return list(uow.audit.list_for(entity, str(world.process.id)))


# --- SaveOpinion: the conclusion is never filled for the person -------------------------------


def test_saving_the_date_the_place_and_the_notes_keeps_the_conclusion_empty(world):
    saved = opinion(world, None, DAY, "Belém", "Nada a declarar.")

    assert saved.conclusion is None
    assert (saved.opinion_date, saved.place, saved.notes) == (DAY, "Belém", "Nada a declarar.")
    assert saved.version == 1
    assert stored_opinion(world) == saved


def test_saving_with_nothing_at_all_creates_the_row_with_no_conclusion(world):
    saved = opinion(world)

    assert saved.conclusion is None
    assert (saved.opinion_date, saved.place, saved.notes) == (None, None, None)
    assert stored_opinion(world) == saved


@pytest.mark.parametrize("conclusion", list(OpinionConclusion))
def test_choosing_the_conclusion_saves_and_audits_it_without_a_justification(world, conclusion):
    saved = opinion(world, conclusion, DAY, "Belém")

    assert stored_opinion(world).conclusion is conclusion
    [event] = events(world, "board_opinion")
    assert event.action is AuditAction.CREATE
    assert event.user_id == world.docente.id
    assert event.justification is None
    assert event.changes["conclusion"]["after"] == conclusion.value
    assert event.changes["opinion_date"]["after"] == DAY.isoformat()
    assert saved.version == 1


def test_clearing_the_conclusion_takes_it_back_to_none(world):
    first = opinion(world, OpinionConclusion.DESFAVORAVEL, DAY)

    cleared = opinion(world, None, DAY, version=first.version)

    assert cleared.conclusion is None
    assert stored_opinion(world).conclusion is None
    assert cleared.version == 2
    assert events(world, "board_opinion")[-1].changes["conclusion"] == {
        "before": "DESFAVORAVEL",
        "after": None,
    }


def test_the_audit_has_counts_and_codes_but_not_the_text_of_the_notes(world):
    opinion(world, OpinionConclusion.FAVORAVEL, DAY, "Belém", "Observação reservada da banca.")

    [event] = events(world, "board_opinion")
    assert event.changes["notes_length"]["after"] == len("Observação reservada da banca.")
    assert "reservada" not in json.dumps(event.changes, ensure_ascii=False)


# --- PAR-13: limits ---------------------------------------------------------------------------


def test_notes_of_5000_characters_are_saved_and_5001_are_a_422_on_notes(world):
    with pytest.raises(ValidationFailed) as raised:
        opinion(world, notes="n" * 5001)
    assert raised.value.field == "notes"
    assert stored_opinion(world) is None

    assert len(opinion(world, notes="n" * 5000).notes) == 5000


def test_a_place_of_100_characters_is_saved_and_101_are_a_422_on_place(world):
    with pytest.raises(ValidationFailed) as raised:
        opinion(world, place="p" * 101)
    assert raised.value.field == "place"
    assert stored_opinion(world) is None

    assert len(opinion(world, place="p" * 100).place) == 100


# --- SaveRequestSettings ----------------------------------------------------------------------


def test_the_city_is_saved_audited_and_never_touches_the_process(world):
    with world.uow_factory() as uow:
        process_before = uow.processes.get(world.process.id)

    saved = city(world, "Belém")

    assert saved.city == "Belém" and saved.version == 1
    assert stored_city(world) == saved
    [event] = events(world, "request_settings")
    assert event.action is AuditAction.CREATE
    assert event.justification is None
    assert event.changes["city_length"]["after"] == len("Belém")
    with world.uow_factory() as uow:
        assert uow.processes.get(world.process.id) == process_before
        assert list(uow.audit.list_for("functional_process", str(world.process.id))) == []


def test_a_city_of_100_characters_is_saved_and_101_are_a_422_on_city(world):
    with pytest.raises(ValidationFailed) as raised:
        city(world, "c" * 101)
    assert raised.value.field == "city"
    assert stored_city(world) is None

    assert len(city(world, "c" * 100).city) == 100


def test_the_city_can_be_cleared(world):
    first = city(world, "Belém")

    cleared = city(world, None, version=first.version)

    assert cleared.city is None and cleared.version == 2
    assert stored_city(world).city is None


# --- versions ---------------------------------------------------------------------------------


@pytest.mark.parametrize("sent", [0, 4])
def test_an_opinion_with_an_outdated_version_is_a_409_with_its_code(world, sent):
    first = opinion(world, OpinionConclusion.FAVORAVEL, DAY)

    with pytest.raises(StaleVersion) as raised:
        opinion(world, OpinionConclusion.DESFAVORAVEL, DAY, version=sent)

    assert raised.value.code == "VERSAO_DESATUALIZADA"
    assert stored_opinion(world) == first


@pytest.mark.parametrize("sent", [0, 4])
def test_a_city_with_an_outdated_version_is_a_409_with_its_code(world, sent):
    first = city(world, "Belém")

    with pytest.raises(StaleVersion) as raised:
        city(world, "Santarém", version=sent)

    assert raised.value.code == "VERSAO_DESATUALIZADA"
    assert stored_city(world) == first


def test_a_first_save_that_expects_a_version_above_zero_is_stale(world):
    with pytest.raises(StaleVersion) as raised:
        opinion(world, version=1)
    assert raised.value.code == "VERSAO_DESATUALIZADA"
    with pytest.raises(StaleVersion) as raised:
        city(world, version=1)
    assert raised.value.code == "VERSAO_DESATUALIZADA"
    assert stored_opinion(world) is None and stored_city(world) is None


# --- BNAV-02, BNAV-03 -------------------------------------------------------------------------


@pytest.mark.parametrize("status", [ProcessStatus.CONCLUIDO, ProcessStatus.ARQUIVADO])
def test_a_closed_process_refuses_both_saves_with_409(world, status):
    set_status(world, status)

    with pytest.raises(Conflict) as raised:
        opinion(world, OpinionConclusion.FAVORAVEL)
    assert raised.value.code == "PROCESSO_SOMENTE_LEITURA"
    with pytest.raises(Conflict) as raised:
        city(world)
    assert raised.value.code == "PROCESSO_SOMENTE_LEITURA"
    assert stored_opinion(world) is None and stored_city(world) is None


@pytest.mark.parametrize("who", ["other_docente", "other_secretaria"])
def test_someone_without_access_gets_not_found_on_both_saves(world, who):
    actor = getattr(world, who)

    with pytest.raises(NotFound):
        opinion(world, actor=actor)
    with pytest.raises(NotFound):
        city(world, actor=actor)
    assert stored_opinion(world) is None and stored_city(world) is None
