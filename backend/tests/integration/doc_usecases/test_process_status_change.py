"""DEL-14, DEL-15: the generic status change refuses CONCLUIDO and the transition check is shared
with the conclusion (a function of the module)."""

import dataclasses

import pytest

from app.application.use_cases.processes import ChangeProcessStatus, check_status_change
from app.domain.entities.audit import AuditAction
from app.domain.entities.process import ProcessStatus
from app.domain.errors import Conflict, Forbidden, NotFound, StaleVersion
from tests.integration.doc_usecases.draft_support import set_status

S = ProcessStatus


def change(world) -> ChangeProcessStatus:
    return ChangeProcessStatus(world.uow_factory, world.audit, world.policy)


def stored(world):
    with world.uow_factory() as uow:
        return uow.processes.get(world.process.id)


def audit_count(world) -> int:
    with world.uow_factory() as uow:
        return len(uow.audit.list_for("process", str(world.process.id)))


@pytest.mark.parametrize("current", [S.RASCUNHO, S.EM_ANDAMENTO])
def test_the_generic_change_refuses_concluido_and_the_process_stays(world, current):
    set_status(world, current)
    before, events = stored(world), audit_count(world)

    with pytest.raises(Conflict) as error:
        change(world).execute(world.admin, world.process.id, S.CONCLUIDO, before.version)

    assert error.value.code == "CONCLUSAO_EXIGE_EXCLUSAO"
    after = stored(world)
    assert (after.status, after.version) == (current, before.version)
    assert audit_count(world) == events


def test_a_process_out_of_reach_is_not_found_even_for_concluido(world):
    set_status(world, S.EM_ANDAMENTO)

    with pytest.raises(NotFound):
        change(world).execute(world.other_docente, world.process.id, S.CONCLUIDO, 2)


def test_rascunho_to_em_andamento_and_arquivado_work_as_before(world):
    started = change(world).execute(world.admin, world.process.id, S.EM_ANDAMENTO, 1)
    archived = change(world).execute(world.admin, world.process.id, S.ARQUIVADO, 2)

    assert started.process.status is S.EM_ANDAMENTO
    assert archived.process.status is S.ARQUIVADO
    with world.uow_factory() as uow:
        events = uow.audit.list_for("process", str(world.process.id))
    assert [e.action for e in events[-2:]] == [AuditAction.STATUS, AuditAction.STATUS]


# --- the transition check shared with the conclusion ----------------------------------------


def test_the_shared_check_accepts_the_forward_transition_of_an_open_process(world):
    in_progress = dataclasses.replace(world.process, status=S.EM_ANDAMENTO, version=3)

    check_status_change(in_progress, world.docente, S.CONCLUIDO, 3)
    check_status_change(world.process, world.admin, S.EM_ANDAMENTO, world.process.version)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (S.CONCLUIDO, S.EM_ANDAMENTO),
        (S.ARQUIVADO, S.CONCLUIDO),
        (S.RASCUNHO, S.CONCLUIDO),
        (S.EM_ANDAMENTO, S.EM_ANDAMENTO),
    ],
)
def test_the_shared_check_refuses_a_transition_outside_the_table(world, current, target):
    process = dataclasses.replace(world.process, status=current)

    with pytest.raises(Conflict):
        check_status_change(process, world.admin, target, process.version)


def test_the_shared_check_applies_the_owner_rule_to_archiving(world):
    process = dataclasses.replace(world.process, status=S.EM_ANDAMENTO)

    check_status_change(process, world.docente, S.ARQUIVADO, process.version)  # the owner
    check_status_change(process, world.admin, S.ARQUIVADO, process.version)
    with pytest.raises(Forbidden):
        check_status_change(process, world.secretaria, S.ARQUIVADO, process.version)


def test_the_shared_check_refuses_a_stale_expected_version(world):
    process = dataclasses.replace(world.process, status=S.EM_ANDAMENTO, version=4)

    with pytest.raises(StaleVersion):
        check_status_change(process, world.admin, S.CONCLUIDO, 3)
