"""FORA-01, FORA-05, FORA-06: a document is outside the interstice only when every dated
activity is outside it."""

import pytest

from app.domain.rules.document_period import document_outside_interstice
from app.domain.rules.scoring_periods import PeriodState

S = PeriodState


def test_every_dated_activity_outside_makes_the_document_outside():
    assert document_outside_interstice([S.FORA]) is True
    assert document_outside_interstice([S.FORA, S.FORA, S.FORA]) is True


def test_one_activity_inside_keeps_the_document_inside():
    assert document_outside_interstice([S.FORA, S.DENTRO]) is False
    assert document_outside_interstice([S.DENTRO, S.FORA]) is False


def test_one_activity_crossing_the_limit_keeps_the_document_inside():
    assert document_outside_interstice([S.FORA, S.PARCIAL]) is False
    assert document_outside_interstice([S.PARCIAL]) is False


def test_without_activities_the_rule_does_not_apply():
    assert document_outside_interstice([]) is False


@pytest.mark.parametrize("state", [S.SEM_DATA, S.NAO_VERIFICAVEL, None])
def test_without_a_usable_date_the_rule_does_not_apply(state):
    assert document_outside_interstice([state]) is False
    assert document_outside_interstice([state, state]) is False


@pytest.mark.parametrize("state", [S.SEM_DATA, S.NAO_VERIFICAVEL, None])
def test_activities_without_a_usable_date_are_ignored_next_to_outside_ones(state):
    assert document_outside_interstice([S.FORA, state]) is True
    assert document_outside_interstice([state, S.DENTRO]) is False
