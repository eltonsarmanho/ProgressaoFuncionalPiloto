"""ATV-08..ATV-13: changing activities, their status and the 'distinct' mark."""

from dataclasses import fields, replace
from datetime import date
from decimal import Decimal

import pytest

from app.application.use_cases.scoring import ActivityData
from app.domain.entities.activity import ActivityStatus, Candidate, Level
from app.domain.entities.audit import AuditAction
from app.domain.entities.process import ProcessStatus
from app.domain.errors import Conflict, NotFound, StaleVersion, ValidationFailed
from app.domain.rules.interstice import Interstice
from app.domain.rules.scoring_alerts import NotScoredReason
from app.domain.rules.scoring_engine import RowStatus, calculate

D = Decimal
INTERSTICE = Interstice(date(2022, 11, 23), date(2024, 11, 23))


def as_data(activity, **changes) -> ActivityData:
    names = {f.name for f in fields(ActivityData)}
    values = {n: getattr(activity, n) for n in names}
    return ActivityData(**{**values, **changes})


@pytest.fixture
def activity(fasi_chosen):
    world = fasi_chosen
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
def test_changing_scoring_inputs_without_justification_is_422(world, activity, changes):
    with pytest.raises(ValidationFailed) as error:
        world.update.execute(
            world.admin, activity.id, as_data(activity, **changes), activity.version, "  "
        )

    assert failing_field(error) == "justificativa"
    with world.uow_factory() as uow:
        assert uow.activities.get(activity.id).version == activity.version


def test_points_override_change_needs_justification(fasi_chosen):
    world = fasi_chosen
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

    with pytest.raises(ValidationFailed) as error:
        world.update.execute(
            world.admin,
            activity.id,
            as_data(activity, points_override=D("24")),
            activity.version,
            None,
        )

    assert failing_field(error) == "justificativa"


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


def test_status_change_requires_justification_and_is_audited(world, activity):
    with pytest.raises(ValidationFailed) as error:
        world.change_status.execute(
            world.admin, activity.id, ActivityStatus.REJEITADA, activity.version, None
        )
    assert failing_field(error) == "justificativa"

    changed = world.change_status.execute(
        world.admin, activity.id, ActivityStatus.REJEITADA, activity.version, "Sem comprovante"
    )

    assert changed.status is ActivityStatus.REJEITADA
    event = events(world, activity)[-1]
    assert event.action is AuditAction.STATUS
    assert event.changes == {"status": {"before": "VALIDADA", "after": "REJEITADA"}}
    assert event.justification == "Sem comprovante"


def test_rejected_back_to_pending_review_counts_as_pending(world, activity):
    rejected = world.change_status.execute(
        world.admin, activity.id, ActivityStatus.REJEITADA, activity.version, "Erro"
    )
    reopened = world.change_status.execute(
        world.admin, activity.id, ActivityStatus.AGUARDANDO_REVISAO, rejected.version, "Revisar"
    )

    result = calculate(world.fasi_version, [reopened], INTERSTICE)

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
    twin = world.create.execute(
        world.admin,
        world.process.id,
        ActivityData(
            title="  orientação de TCC ",
            group_number=2,
            item_number=7,
            quantity=D("1"),
            event_date=date(2023, 5, 10),
        ),
    )
    with world.uow_factory() as uow:
        both = uow.activities.list_for_process(world.process.id)
    assert calculate(world.fasi_version, both, INTERSTICE).rows[1].reasons == (
        NotScoredReason.DUPLICIDADE,
    )

    with pytest.raises(ValidationFailed) as error:
        world.mark_distinct.execute(world.admin, twin.id, twin.version, " ")
    assert failing_field(error) == "justificativa"

    world.mark_distinct.execute(world.admin, twin.id, twin.version, "Outro aluno")

    with world.uow_factory() as uow:
        both = uow.activities.list_for_process(world.process.id)
    result = calculate(world.fasi_version, both, INTERSTICE)
    assert [r.status for r in result.rows] == [RowStatus.PONTUADA, RowStatus.PONTUADA]
    assert result.group_subtotals[2] == D("50")
    event = events(world, twin)[-1]
    assert event.justification == "Outro aluno"
    assert event.changes == {"distinct_justification": {"before": None, "after": "Outro aluno"}}


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
    result = calculate(world.fasi_version, [updated], INTERSTICE)
    assert result.group_subtotals[2] == D("40")
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
