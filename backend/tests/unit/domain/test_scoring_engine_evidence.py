"""VINC-04, VINC-06: linked documents count as evidence in the scoring engine."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.domain.entities.activity import ActivityStatus
from app.domain.rules.scoring_alerts import NotScoredReason, ScoringAlertCode
from app.domain.rules.scoring_engine import RowStatus, calculate
from tests.unit.domain.test_scoring_engine import BASIC, INTERSTICE, act, row_of


def alert_codes(result, activity):
    return [a.code for a in row_of(result, activity).alerts]


def test_activity_with_a_link_and_no_note_counts_as_evidenced_and_has_no_missing_proof_alert():
    a = act(evidence_note=None)

    result = calculate(BASIC, [a], INTERSTICE, {a.id: 1})

    assert result.counters.with_evidence == 1
    assert ScoringAlertCode.SEM_COMPROVANTE not in alert_codes(result, a)
    assert row_of(result, a).evidence_count == 1


def test_activity_with_neither_link_nor_note_emits_the_missing_proof_alert():
    a = act(evidence_note=None)

    result = calculate(BASIC, [a], INTERSTICE, {a.id: 0})

    assert result.counters.with_evidence == 0
    assert ScoringAlertCode.SEM_COMPROVANTE in alert_codes(result, a)
    assert row_of(result, a).evidence_count == 0


@pytest.mark.parametrize("note", ["", "   "])
def test_a_blank_note_is_not_evidence(note):
    a = act(evidence_note=note)

    result = calculate(BASIC, [a], INTERSTICE, {})

    assert result.counters.with_evidence == 0
    assert ScoringAlertCode.SEM_COMPROVANTE in alert_codes(result, a)


def test_activity_with_a_note_and_no_link_counts_and_does_not_emit_as_before():
    a = act(evidence_note="Certificado")

    result = calculate(BASIC, [a], INTERSTICE, {a.id: 0})

    assert result.counters.with_evidence == 1
    assert ScoringAlertCode.SEM_COMPROVANTE not in alert_codes(result, a)
    assert row_of(result, a).evidence_count == 0


def test_activity_with_both_a_note_and_several_links_counts_once():
    a = act(evidence_note="Certificado")

    result = calculate(BASIC, [a], INTERSTICE, {a.id: 3})

    assert result.counters.with_evidence == 1
    assert row_of(result, a).evidence_count == 3


def test_links_of_one_activity_do_not_cover_another():
    linked, bare = act(evidence_note=None), act(evidence_note=None)

    result = calculate(BASIC, [linked, bare], INTERSTICE, {linked.id: 2})

    assert result.counters.with_evidence == 1
    assert ScoringAlertCode.SEM_COMPROVANTE not in alert_codes(result, linked)
    assert ScoringAlertCode.SEM_COMPROVANTE in alert_codes(result, bare)
    assert (row_of(result, linked).evidence_count, row_of(result, bare).evidence_count) == (2, 0)


def test_counters_with_evidence_add_links_and_notes():
    by_note = act(evidence_note="Certificado")
    by_link = act(evidence_note=None)
    by_both = act(evidence_note="Ata")
    by_neither = act(evidence_note=None)

    result = calculate(
        BASIC, [by_note, by_link, by_both, by_neither], INTERSTICE, {by_link.id: 1, by_both.id: 1}
    )

    assert result.counters.activities == 4
    assert result.counters.with_evidence == 3


def test_activities_that_are_not_scored_still_report_their_links_and_count_as_evidenced():
    rejected = act(evidence_note=None, status=ActivityStatus.REJEITADA)

    result = calculate(BASIC, [rejected], INTERSTICE, {rejected.id: 2})

    row = row_of(result, rejected)
    assert row.status is RowStatus.NAO_PONTUADA
    assert row.reasons == (NotScoredReason.REJEITADA,)
    assert row.evidence_count == 2
    assert result.counters.with_evidence == 1


def test_unknown_ids_in_the_counts_are_ignored():
    a = act(evidence_note=None)

    result = calculate(BASIC, [a], INTERSTICE, {uuid4(): 5})

    assert result.counters.with_evidence == 0
    assert ScoringAlertCode.SEM_COMPROVANTE in alert_codes(result, a)


def test_without_the_argument_the_result_is_the_same_as_with_empty_counts():
    with_note, without_note = act(evidence_note="Certificado"), act(evidence_note=None)
    activities = [with_note, without_note]

    assert calculate(BASIC, activities, INTERSTICE) == calculate(BASIC, activities, INTERSTICE, {})
    assert calculate(BASIC, activities, INTERSTICE).counters.with_evidence == 1


def test_links_change_neither_points_nor_totals():
    a = act(quantity="4", evidence_note=None)

    plain = calculate(BASIC, [a], INTERSTICE)
    linked = calculate(BASIC, [a], INTERSTICE, {a.id: 1})

    assert (linked.total, linked.group_subtotals) == (plain.total, plain.group_subtotals)
    assert row_of(linked, a).points == row_of(plain, a).points


def test_duplicates_sharing_a_linked_document_are_still_excluded_without_double_counting():
    older = act(title="Banca X", quantity="2", created_at=datetime(2025, 1, 1, tzinfo=UTC))
    newer = act(title="banca x", quantity="2", created_at=datetime(2025, 1, 2, tzinfo=UTC))

    result = calculate(BASIC, [older, newer], INTERSTICE, {older.id: 1, newer.id: 1})

    assert row_of(result, older).status is RowStatus.PONTUADA
    assert row_of(result, newer).status is RowStatus.NAO_PONTUADA
    assert row_of(result, newer).reasons == (NotScoredReason.DUPLICIDADE,)
    assert result.total == row_of(result, older).points
