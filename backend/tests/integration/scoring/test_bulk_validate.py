"""REV-02, REV-03, REV-04: validating several suggested activities at once."""

import dataclasses
import uuid

import pytest

from app.application.use_cases import scoring
from app.application.use_cases.scoring import ActivityData
from app.domain.entities.activity import ActivitySource, ActivityStatus
from app.domain.entities.audit import AuditAction
from app.domain.entities.process import ProcessStatus
from app.domain.errors import Conflict, NotFound, ValidationFailed


@pytest.fixture
def bulk(world):
    return scoring.BulkValidateActivities(world.uow_factory, world.audit, world.policy)


def draft(world, title, process=None):
    return world.create.execute(
        world.admin,
        (process or world.process).id,
        ActivityData(title=title, group_number=3, item_number=4),
        source=ActivitySource.SUGERIDA_IA,
    )


def reload(world, activity):
    with world.uow_factory() as uow:
        return uow.activities.get(activity.id)


def audit_of(world, activity):
    with world.uow_factory() as uow:
        return list(uow.audit.list_for("activity", str(activity.id)))


def test_three_selected_drafts_become_validated_with_the_same_justification_and_three_events(
    world, bulk
):
    drafts = [draft(world, f"Sugerida {n}") for n in range(3)]

    result = bulk.execute(world.docente, world.process.id, [a.id for a in drafts], "Conferi todas")

    assert [a.status for a in result] == [ActivityStatus.VALIDADA] * 3
    assert [a.id for a in result] == [a.id for a in drafts]
    for activity in drafts:
        assert reload(world, activity).status is ActivityStatus.VALIDADA
        created, status_event = audit_of(world, activity)
        assert created.action is AuditAction.CREATE
        assert status_event.action is AuditAction.STATUS
        assert status_event.user_id == world.docente.id
        assert status_event.justification == "Conferi todas"
        assert status_event.changes == {
            "status": {"before": "AGUARDANDO_REVISAO", "after": "VALIDADA"}
        }


@pytest.mark.parametrize("justification", [None, "", "   "])
def test_without_a_justification_nothing_is_validated(world, bulk, justification):
    drafts = [draft(world, "A"), draft(world, "B")]

    with pytest.raises(ValidationFailed) as error:
        bulk.execute(world.docente, world.process.id, [a.id for a in drafts], justification)

    assert error.value.field == "justificativa"
    assert [reload(world, a).status for a in drafts] == [ActivityStatus.AGUARDANDO_REVISAO] * 2


def test_an_activity_of_another_process_gives_404_and_validates_none(world, bulk, add_process):
    other = add_process()
    mine = draft(world, "Minha")
    foreign = draft(world, "De outro processo", process=other)
    later = draft(world, "Depois")

    with pytest.raises(NotFound):
        bulk.execute(
            world.admin, world.process.id, [mine.id, foreign.id, later.id], "Conferi"
        )

    for activity in (mine, foreign, later):
        assert reload(world, activity).status is ActivityStatus.AGUARDANDO_REVISAO
        assert len(audit_of(world, activity)) == 1  # only its creation


def test_an_unknown_activity_gives_404_and_validates_none(world, bulk):
    mine = draft(world, "Minha")

    with pytest.raises(NotFound):
        bulk.execute(world.admin, world.process.id, [mine.id, uuid.uuid4()], "Conferi")

    assert reload(world, mine).status is ActivityStatus.AGUARDANDO_REVISAO


def test_only_the_selected_activities_are_validated(world, bulk):
    selected, left_out = draft(world, "Selecionada"), draft(world, "Esquecida")

    bulk.execute(world.docente, world.process.id, [selected.id], "Conferi")

    assert reload(world, selected).status is ActivityStatus.VALIDADA
    assert reload(world, left_out).status is ActivityStatus.AGUARDANDO_REVISAO
    assert len(audit_of(world, left_out)) == 1


def test_suggested_activities_stay_pending_until_the_explicit_call(world):
    suggested = draft(world, "Sugerida")

    world.list_activities.execute(world.docente, world.process.id)
    world.calc.execute(world.docente, world.process.id)

    assert reload(world, suggested).status is ActivityStatus.AGUARDANDO_REVISAO


def test_already_validated_activities_are_left_alone_and_get_no_new_event(world, bulk):
    pending = draft(world, "Pendente")
    done = draft(world, "Ja validada")
    world.change_status.execute(
        world.admin, done.id, ActivityStatus.VALIDADA, done.version, "Antes"
    )

    result = bulk.execute(world.docente, world.process.id, [pending.id, done.id], "Agora")

    assert [a.status for a in result] == [ActivityStatus.VALIDADA] * 2
    assert len(audit_of(world, done)) == 2  # creation and the earlier validation
    assert audit_of(world, done)[-1].justification == "Antes"
    assert len(audit_of(world, pending)) == 2


def test_a_repeated_id_is_validated_once(world, bulk):
    only = draft(world, "Unica")

    result = bulk.execute(world.docente, world.process.id, [only.id, only.id], "Conferi")

    assert len(result) == 1
    assert len(audit_of(world, only)) == 2


def test_without_access_the_process_is_not_found(world, bulk):
    pending = draft(world, "Pendente")

    for actor in (world.other_docente, world.other_secretaria):
        with pytest.raises(NotFound):
            bulk.execute(actor, world.process.id, [pending.id], "Conferi")
    with pytest.raises(NotFound):
        bulk.execute(world.admin, uuid.uuid4(), [pending.id], "Conferi")
    assert reload(world, pending).status is ActivityStatus.AGUARDANDO_REVISAO


@pytest.mark.parametrize("status", [ProcessStatus.CONCLUIDO, ProcessStatus.ARQUIVADO])
def test_closed_process_gives_409(world, bulk, add_process, status):
    process = add_process()
    pending = draft(world, "Pendente", process=process)
    with world.uow_factory() as uow:
        current = uow.processes.get(process.id)
        uow.processes.update(dataclasses.replace(current, status=status), current.version)
        uow.commit()

    with pytest.raises(Conflict):
        bulk.execute(world.admin, process.id, [pending.id], "Conferi")

    assert reload(world, pending).status is ActivityStatus.AGUARDANDO_REVISAO
