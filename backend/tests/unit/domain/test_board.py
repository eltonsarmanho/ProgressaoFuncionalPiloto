"""PORT-02, PORT-05, PORT-07, PAR-01, PAR-12, DOS-03: the board, ordinance and opinion entities."""

import dataclasses
from itertools import product
from uuid import uuid4

import pytest

from app.domain.entities.board import (
    BoardMember,
    BoardOpinion,
    BoardOrdinance,
    BoardRole,
    OpinionConclusion,
    OrdinanceReadingCode,
    OrdinanceWarningCode,
    ReadingState,
    RequestSettings,
    ValueSource,
    can_read_transition,
)


def test_the_board_roles_are_the_three_of_the_ordinance():
    assert [r.value for r in BoardRole] == ["PRESIDENTE", "MEMBRO", "SUPLENTE"]


def test_a_value_comes_from_the_extraction_or_from_the_person():
    assert [s.value for s in ValueSource] == ["EXTRAIDO", "INFORMADO"]


def test_the_reading_states_are_the_five_of_the_ordinance():
    assert [s.value for s in ReadingState] == [
        "SEM_ARQUIVO",
        "PENDENTE",
        "LENDO",
        "LIDA",
        "FALHOU",
    ]


def test_the_opinion_conclusion_is_favorable_or_unfavorable():
    assert [c.value for c in OpinionConclusion] == ["FAVORAVEL", "DESFAVORAVEL"]


def test_the_reading_failure_codes_are_the_six_of_the_design():
    assert [c.value for c in OrdinanceReadingCode] == [
        "IA_INDISPONIVEL",
        "IA_CREDENCIAL_RECUSADA",
        "RESPOSTA_INVALIDA",
        "TEXTO_ILEGIVEL",
        "INTERROMPIDA",
        "ERRO_INTERNO",
    ]


def test_the_ordinance_warning_codes_are_the_two_of_the_spec():
    assert [c.value for c in OrdinanceWarningCode] == [
        "VALOR_SEM_ORIGEM",
        "MEMBROS_NAO_ENCONTRADOS",
    ]


def test_a_new_opinion_has_no_conclusion_date_or_place_and_no_notes_field():
    opinion = BoardOpinion(process_id=uuid4())

    assert opinion.conclusion is None
    assert opinion.opinion_date is None
    assert not opinion.place
    assert [f.name for f in dataclasses.fields(opinion)] == [
        "process_id",
        "conclusion",
        "opinion_date",
        "place",
        "version",
    ]


def test_a_new_ordinance_is_without_file_and_without_members():
    ordinance = BoardOrdinance(process_id=uuid4())

    assert ordinance.reading_state is ReadingState.SEM_ARQUIVO
    assert ordinance.members == ()
    assert ordinance.file is None
    assert ordinance.is_registered is False


def test_an_ordinance_with_one_member_is_registered():
    member = BoardMember("Maria Souza", BoardRole.PRESIDENTE, 1, ValueSource.EXTRAIDO)

    ordinance = BoardOrdinance(process_id=uuid4(), members=(member,))

    assert ordinance.is_registered is True


def test_the_request_settings_start_without_a_city():
    assert RequestSettings(process_id=uuid4()).city is None


_ALLOWED = {
    (ReadingState.SEM_ARQUIVO, ReadingState.PENDENTE),
    (ReadingState.PENDENTE, ReadingState.LENDO),
    (ReadingState.LENDO, ReadingState.LIDA),
    (ReadingState.LENDO, ReadingState.FALHOU),
    (ReadingState.LIDA, ReadingState.PENDENTE),
    (ReadingState.FALHOU, ReadingState.PENDENTE),
}


@pytest.mark.parametrize(("current", "target"), sorted(_ALLOWED))
def test_a_reading_may_move_along_the_allowed_transitions(current, target):
    assert can_read_transition(current, target) is True


@pytest.mark.parametrize(
    ("current", "target"),
    [pair for pair in product(ReadingState, ReadingState) if pair not in _ALLOWED],
)
def test_every_other_reading_transition_is_refused(current, target):
    assert can_read_transition(current, target) is False
