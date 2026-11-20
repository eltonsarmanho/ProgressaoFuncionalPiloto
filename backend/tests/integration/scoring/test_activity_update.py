"""ATV-08..ATV-13: changing activities, their status and the 'distinct' mark."""

from dataclasses import fields, replace
from datetime import date
from decimal import Decimal

import pytest

from app.application.use_cases.scoring import ActivityData, compute_process_score
from app.domain.entities.activity import ActivityStatus, Candidate, Level
from app.domain.entities.audit import AuditAction
from app.domain.entities.process import ProcessStatus
from app.domain.errors import Conflict, NotFound, StaleVersion, ValidationFailed
from app.domain.rules.activity_validity import InvalidReason
from app.domain.rules.interstice import Interstice
from app.domain.rules.scoring_engine import RowStatus, calculate
from tests.support.legacy_duplicates import add_legacy_duplicate

D = Decimal
INTERSTICE = Interstice(date(2022, 11, 23), date(2024, 11, 23))


def as_data(activity, **changes) -> ActivityData:
    names = {f.name for f in fields(ActivityData)}
    values = {n: getattr(activity, n) for n in names}
    return ActivityData(**{**values, **changes})


@pytest.fixture
def activity(official_chosen):
    world = official_chosen
    return world.create.execute(
        world.admin,
        world.process.id,
        ActivityData(
            title="Orientação de TCC",
            group_number=2,
            item_number=7,
            quantity=D("4"),
            event_date=date(2023, 5, 10),
            evidence_note="Declaração",
        ),
    )


def events(world, activity):
    with world.uow_factory() as uow:
        return uow.audit.list_for("activity", str(activity.id))


def failing_field(error) -> str:
    return error.value.field


@pytest.mark.parametrize(
    "changes",
    [
        {"group_number": 3, "item_number": 2},
        {"item_number": 8},
        {"quantity": D("5")},
        {"hours": D("10")},
        {"informed_points": D("3")},
    ],
)
def test_changing_scoring_inputs_without_justification_is_saved_and_audited(
    world, activity, changes
):
    """UIM-16: item, quantity, hours and points change without a justification."""
    updated = world.update.execute(
        world.admin, activity.id, as_data(activity, **changes), activity.version, "  "
    )

    assert updated.version == activity.version + 1
    for field, value in changes.items():
        assert getattr(updated, field) == value
    event = events(world, activity)[-1]
    assert event.action is AuditAction.UPDATE
    assert event.justification is None
    assert set(event.changes) == set(changes)


def test_changing_the_category_of_a_validated_activity_recalculates_and_keeps_it_validated(
    world, activity
):
    """Edge case of the spec: the status stays VALIDADA and the points follow the new item."""
    assert activity.status is ActivityStatus.VALIDADA
    old, new = (
        world.official_version.get_criterion(2, 7),
        world.official_version.get_criterion(2, 8),
    )
    assert old.unit_points != new.unit_points  # the test would prove nothing otherwise

    def scored_points():
        with world.uow_factory() as uow:
            score = compute_process_score(uow, uow.processes.get(world.process.id))
        [row] = score.result.rows
        return row.status, row.points, score.result.total

    before = scored_points()

    changed = world.update.execute(
        world.admin, activity.id, as_data(activity, item_number=8), activity.version, None
    )

    assert changed.status is ActivityStatus.VALIDADA
    after = scored_points()
    assert before == (RowStatus.PONTUADA, old.unit_points * 4, old.unit_points * 4)
    assert after == (RowStatus.PONTUADA, new.unit_points * 4, new.unit_points * 4)


def test_points_override_change_needs_no_justification(points_chosen):
    world = points_chosen
    activity = world.create.execute(
        world.admin,
        world.process.id,
        ActivityData(
            title="Disciplina",
            group_number=1,
            academic_period="2023.1",
            level=Level.GRADUACAO,
            hours=D("68"),
            event_date=date(2023, 3, 1),
        ),
    )

    updated = world.update.execute(
        world.admin,
        activity.id,
        as_data(activity, points_override=D("24")),
        activity.version,
        None,
    )

    assert updated.points_override == D("24")
    event = events(world, activity)[-1]
    assert event.changes["points_override"] == {"before": None, "after": "24"}
    assert event.justification is None


def test_unit_points_override_survives_a_quantity_change_and_clears_when_empty(world, activity):
    """UIM-21: the typed unit value stays after other edits; None goes back to the table."""
    typed = world.update.execute(
        world.admin,
        activity.id,
        as_data(activity, unit_points_override=D("2.5")),
        activity.version,
        None,
    )
    assert typed.unit_points_override == D("2.5")
    event = events(world, activity)[-1]
    assert event.changes == {"unit_points_override": {"before": None, "after": "2.5"}}
    assert event.justification is None

    more = world.update.execute(
        world.admin, activity.id, as_data(typed, quantity=D("6")), typed.version, None
    )
    assert (more.quantity, more.unit_points_override) == (D("6"), D("2.5"))
    assert calculate(world.official_version, [more], INTERSTICE).rows[0].points == D("15")

    cleared = world.update.execute(
        world.admin, activity.id, as_data(more, unit_points_override=None), more.version, None
    )
    assert cleared.unit_points_override is None
    assert events(world, activity)[-1].changes == {
        "unit_points_override": {"before": "2.5", "after": None}
    }
    assert calculate(world.official_version, [cleared], INTERSTICE).rows[0].points == D("30")


def test_unit_points_override_is_refused_when_the_item_changes_to_one_without_unit_value(
    world, activity
):
    typed = world.update.execute(
        world.admin,
        activity.id,
        as_data(activity, unit_points_override=D("2.5")),
        activity.version,
        None,
    )

    with pytest.raises(ValidationFailed) as error:
        world.update.execute(
            world.admin,
            activity.id,
            as_data(typed, group_number=None, item_number=None),
            typed.version,
            None,
        )

    assert error.value.field == "unit_points_override"


def test_justified_change_is_saved_and_audited_with_before_and_after(world, activity):
    updated = world.update.execute(
        world.secretaria,
        activity.id,
        as_data(activity, quantity=D("5")),
        activity.version,
        "Mais uma orientação",
    )

    assert updated.quantity == D("5")
    assert updated.version == activity.version + 1
    event = events(world, activity)[-1]
    assert (event.action, event.user_id) == (AuditAction.UPDATE, world.secretaria.id)
    assert event.changes == {"quantity": {"before": "4", "after": "5"}}
    assert event.justification == "Mais uma orientação"


def test_descriptive_fields_change_without_justification(world, activity):
    updated = world.update.execute(
        world.admin,
        activity.id,
        as_data(activity, title="Orientação de TCC (2023)", evidence_note="Ata"),
        activity.version,
        None,
    )

    assert (updated.title, updated.evidence_note) == ("Orientação de TCC (2023)", "Ata")
    assert events(world, activity)[-1].changes["evidence_note"] == {
        "before": "Declaração",
        "after": "Ata",
    }


def test_update_applies_the_same_input_validation(world, activity):
    with pytest.raises(ValidationFailed) as error:
        world.update.execute(
            world.admin, activity.id, as_data(activity, quantity=D("-2")), activity.version, "x"
        )

    assert failing_field(error) == "quantidade"


@pytest.mark.parametrize("justification", [None, "", "  "])
def test_status_change_without_justification_is_audited_without_one(world, activity, justification):
    """UIM-14: validating, rejecting and reopening need no justification."""
    changed = world.change_status.execute(
        world.admin, activity.id, ActivityStatus.REJEITADA, activity.version, justification
    )

    assert changed.status is ActivityStatus.REJEITADA
    event = events(world, activity)[-1]
    assert event.action is AuditAction.STATUS
    assert event.changes == {"status": {"before": "VALIDADA", "after": "REJEITADA"}}
    assert event.justification is None


def test_status_change_with_a_justification_stores_it_in_the_audit_event(world, activity):
    world.change_status.execute(
        world.admin, activity.id, ActivityStatus.REJEITADA, activity.version, "Sem comprovante"
    )

    assert events(world, activity)[-1].justification == "Sem comprovante"


def test_rejected_back_to_pending_review_counts_as_pending(world, activity):
    rejected = world.change_status.execute(
        world.admin, activity.id, ActivityStatus.REJEITADA, activity.version, "Erro"
    )
    reopened = world.change_status.execute(
        world.admin, activity.id, ActivityStatus.AGUARDANDO_REVISAO, rejected.version, "Revisar"
    )

    result = calculate(world.official_version, [reopened], INTERSTICE)

    assert reopened.status is ActivityStatus.AGUARDANDO_REVISAO
    assert result.rows[0].status is RowStatus.POTENCIAL
    assert result.counters.pending == 1
    assert result.total == 0
    assert [e.changes["status"]["after"] for e in events(world, activity)[-2:]] == [
        "REJEITADA",
        "AGUARDANDO_REVISAO",
    ]


def test_same_status_is_rejected_on_the_status_field(world, activity):
    with pytest.raises(ValidationFailed) as error:
        world.change_status.execute(
            world.admin, activity.id, ActivityStatus.VALIDADA, activity.version, "x"
        )

    assert failing_field(error) == "status"


def test_distinct_mark_releases_the_duplicate_and_audits_the_justification(world, activity):
    # DUP-04: a write merges duplicates now, so the twin is a row from before the merge
    twin = add_legacy_duplicate(
        world.uow_factory, activity, title="  orientação de TCC ", quantity=D("1")
    )
    with world.uow_factory() as uow:
        both = uow.activities.list_for_process(world.process.id)
    # SEG-01: the duplicate is not valid and has no row
    before = calculate(world.official_version, both, INTERSTICE)
    assert len(before.rows) == 1
    assert before.validity[twin.id].reason is InvalidReason.DUPLICIDADE

    world.mark_distinct.execute(world.admin, twin.id, twin.version, "Outro aluno")

    with world.uow_factory() as uow:
        both = uow.activities.list_for_process(world.process.id)
    result = calculate(world.official_version, both, INTERSTICE)
    assert [r.status for r in result.rows] == [RowStatus.PONTUADA, RowStatus.PONTUADA]
    assert result.group_subtotals[2] == D("25")
    event = events(world, twin)[-1]
    assert event.justification == "Outro aluno"
    assert event.changes == {"distinct_justification": {"before": None, "after": "Outro aluno"}}


@pytest.mark.parametrize("justification", [None, "", "  "])
def test_distinct_mark_without_justification_still_releases_the_duplicate(
    world, activity, justification
):
    """UIM-14: the mark itself is what counts both activities; the text is optional."""
    # DUP-04: a write merges duplicates now, so the twin is a row from before the merge
    twin = add_legacy_duplicate(world.uow_factory, activity, title="orientação de TCC",
                                quantity=D("1"))  # fmt: skip

    marked = world.mark_distinct.execute(world.admin, twin.id, twin.version, justification)

    with world.uow_factory() as uow:
        both = uow.activities.list_for_process(world.process.id)
    result = calculate(world.official_version, both, INTERSTICE)
    assert [r.status for r in result.rows] == [RowStatus.PONTUADA, RowStatus.PONTUADA]
    assert marked.distinct_justification == "Marcada como distinta pelo usuário"
    assert events(world, twin)[-1].justification is None


def test_only_the_chosen_candidate_item_scores(world, activity):
    candidate = Candidate(4, 2, "Também cabe em extensão")

    updated = world.update.execute(
        world.admin,
        activity.id,
        as_data(activity, candidates=(candidate,)),
        activity.version,
        None,
    )

    assert updated.candidates == (candidate,)
    result = calculate(world.official_version, [updated], INTERSTICE)
    assert result.group_subtotals[2] == D("20")
    assert result.group_subtotals[4] == 0
    assert events(world, activity)[-1].changes["candidates"]["after"] == [
        {"group_number": 4, "item_number": 2, "justification": "Também cabe em extensão"}
    ]


def test_second_write_with_same_version_is_a_conflict(world, activity):
    world.update.execute(
        world.admin, activity.id, as_data(activity, quantity=D("5")), activity.version, "Primeira"
    )

    with pytest.raises(StaleVersion):
        world.update.execute(
            world.admin,
            activity.id,
            as_data(activity, quantity=D("6")),
            activity.version,
            "Segunda",
        )
    with pytest.raises(StaleVersion):
        world.change_status.execute(
            world.admin, activity.id, ActivityStatus.REJEITADA, activity.version, "x"
        )
    with pytest.raises(StaleVersion):
        world.mark_distinct.execute(world.admin, activity.id, activity.version, "x")
    with world.uow_factory() as uow:
        assert uow.activities.get(activity.id).quantity == D("5")


@pytest.mark.parametrize("status", [ProcessStatus.CONCLUIDO, ProcessStatus.ARQUIVADO])
def test_closed_process_rejects_every_write(world, activity, status):
    with world.uow_factory() as uow:
        process = uow.processes.get(world.process.id)
        uow.processes.update(replace(process, status=status), process.version)
        uow.commit()

    with pytest.raises(Conflict):
        world.update.execute(
            world.admin, activity.id, as_data(activity, title="Novo"), activity.version, None
        )
    with pytest.raises(Conflict):
        world.change_status.execute(
            world.admin, activity.id, ActivityStatus.REJEITADA, activity.version, "x"
        )
    with pytest.raises(Conflict):
        world.mark_distinct.execute(world.admin, activity.id, activity.version, "x")


@pytest.mark.parametrize("actor", ["other_docente", "other_secretaria"])
def test_activity_outside_access_is_not_found(world, activity, actor):
    user = getattr(world, actor)

    with pytest.raises(NotFound):
        world.update.execute(user, activity.id, as_data(activity), activity.version, None)
    with pytest.raises(NotFound):
        world.change_status.execute(
            user, activity.id, ActivityStatus.REJEITADA, activity.version, "x"
        )
    with pytest.raises(NotFound):
        world.mark_distinct.execute(user, activity.id, activity.version, "x")


# --- CAEDI-01..03: a stored manual score the item does not accept -----------------------------

_REFUSAL = (
    "Esta tabela não aceita pontuação manual neste item; nos itens por unidade ou por bloco de "
    "horas, informe o valor unitário"
)
_PIT_REFUSAL = (
    "No Grupo I, as horas de PIT são calculadas da carga horária; não há pontos a informar"
)
_UNACCEPTED_KINDS = {
    "por_unidade": (dict(group_number=2, item_number=7, quantity=D("4")), _REFUSAL),
    "pit": (
        dict(group_number=1, academic_period="2023.1", level=Level.GRADUACAO, hours=D("68")),
        _PIT_REFUSAL,
    ),
    "sem_item": (dict(), _REFUSAL),
}


def stored_with_override(world, **fields):
    """An activity whose `points_override` was written by the repository, as old data was."""
    created = world.create.execute(
        world.admin,
        world.process.id,
        ActivityData(title="Disciplina", event_date=date(2023, 5, 10), **fields),
    )
    with world.uow_factory() as uow:
        uow.activities.update(replace(created, points_override=D("24")), created.version)
        uow.commit()
        return uow.activities.get(created.id)


def reload(world, activity):
    with world.uow_factory() as uow:
        return uow.activities.get(activity.id)


@pytest.mark.parametrize("kind", _UNACCEPTED_KINDS)
def test_editing_with_the_same_refused_manual_score_clears_it_and_audits_the_old_value(
    official_chosen, kind
):
    world = official_chosen
    stored = stored_with_override(world, **_UNACCEPTED_KINDS[kind][0])
    assert stored.points_override == D("24")

    updated = world.update.execute(
        world.admin, stored.id, as_data(stored, title="Título novo"), stored.version, None
    )

    assert (updated.title, updated.points_override) == ("Título novo", None)
    assert reload(world, stored).points_override is None
    event = events(world, stored)[-1]
    assert event.action is AuditAction.UPDATE
    assert event.changes["points_override"] == {"before": "24", "after": None}


@pytest.mark.parametrize("kind", _UNACCEPTED_KINDS)
def test_editing_with_a_different_refused_manual_score_is_422_and_saves_nothing(
    official_chosen, kind
):
    world = official_chosen
    fields, message = _UNACCEPTED_KINDS[kind]
    stored = stored_with_override(world, **fields)

    with pytest.raises(ValidationFailed) as error:
        world.update.execute(
            world.admin,
            stored.id,
            as_data(stored, title="Título novo", points_override=D("25")),
            stored.version,
            None,
        )

    assert (error.value.field, error.value.message) == ("points_override", message)
    after = reload(world, stored)
    assert (after.title, after.points_override, after.version) == (
        "Disciplina",
        D("24"),
        stored.version,
    )


def test_editing_keeps_the_stored_manual_score_where_the_item_accepts_it(points_chosen):
    world = points_chosen
    stored = stored_with_override(
        world, group_number=1, academic_period="2023.1", level=Level.GRADUACAO, hours=D("68")
    )

    updated = world.update.execute(
        world.admin, stored.id, as_data(stored, title="Título novo"), stored.version, None
    )

    assert (updated.title, updated.points_override) == ("Título novo", D("24"))
    assert reload(world, stored).points_override == D("24")
