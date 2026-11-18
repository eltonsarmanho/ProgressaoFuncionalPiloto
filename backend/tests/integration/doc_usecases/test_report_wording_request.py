"""REL-03, REL-13: asking for the wording of a section in the background."""

import pytest

from app.domain.entities.audit import AuditAction
from app.domain.entities.generated import GenerationCode, GenerationState
from app.domain.entities.process import ProcessStatus
from app.domain.errors import Conflict, NotFound
from tests.integration.doc_usecases.draft_support import (
    list_wording_uc,
    request_wording_uc,
    save_proposal,
    set_status,
    stored_draft,
)
from tests.integration.doc_usecases.generation_support import add_activity


def ask(gen, section="1.3", actor=None):
    world = gen.world
    return request_wording_uc(world, gen.clock).execute(
        actor or world.docente, world.process.id, section
    )


def jobs(world):
    with world.uow_factory() as uow:
        return uow.wording_jobs.latest_by_section(world.process.id)


def finish(world, job, state=GenerationState.PRONTO):
    with world.uow_factory() as uow:
        uow.wording_jobs.claim_next(job.requested_at)
        uow.wording_jobs.finish(job.id, job.requested_at, state)
        uow.commit()


def test_the_request_answers_at_once_with_a_generating_job_and_saves_the_proposal(gen):
    world = gen.world
    add_activity(world)

    job = ask(gen)

    assert (job.section_key, job.state) == ("1.3", GenerationState.GERANDO)
    assert (job.requested_by, job.requested_at) == (world.docente.id, gen.clock.now())
    assert (job.started_at, job.finished_at, job.error_code) == (None, None, None)
    assert jobs(world)["1.3"] == job
    assert stored_draft(world).version == 1
    with world.uow_factory() as uow:
        [event] = uow.audit.list_for("report_wording_job", str(job.id))
    assert event.action is AuditAction.CREATE
    assert event.changes["state"]["after"] == "GERANDO"


def test_a_saved_draft_keeps_its_version_when_the_wording_is_asked(gen):
    world = gen.world
    add_activity(world)
    saved = save_proposal(world)

    ask(gen)

    assert stored_draft(world) == saved


def test_a_second_request_of_the_same_section_is_a_409_and_another_section_is_accepted(gen):
    world = gen.world
    add_activity(world)
    first = ask(gen, "1.3")

    with pytest.raises(Conflict) as error:
        ask(gen, "1.3")
    other = ask(gen, "2")

    assert error.value.code == GenerationCode.REDACAO_EM_ANDAMENTO
    latest = jobs(world)
    assert (latest["1.3"].id, latest["2"].id) == (first.id, other.id)
    assert latest["2"].state is GenerationState.GERANDO


def test_once_the_job_is_closed_the_section_can_be_asked_again(gen):
    world = gen.world
    add_activity(world)
    first = ask(gen)
    finish(world, first, GenerationState.FALHOU)
    gen.clock.advance(minutes=1)

    second = ask(gen)

    assert second.id != first.id
    assert jobs(world)["1.3"].id == second.id


@pytest.mark.parametrize("status", [ProcessStatus.CONCLUIDO, ProcessStatus.ARQUIVADO])
def test_a_concluded_or_archived_process_refuses_the_request_and_creates_nothing(gen, status):
    world = gen.world
    add_activity(world)
    set_status(world, status)

    with pytest.raises(Conflict) as error:
        ask(gen)

    assert error.value.code == GenerationCode.PROCESSO_SOMENTE_LEITURA
    assert jobs(world) == {}
    assert stored_draft(world) is None


def test_a_process_out_of_reach_or_a_section_that_does_not_exist_is_not_found(gen):
    world = gen.world
    add_activity(world)

    with pytest.raises(NotFound):
        ask(gen, actor=world.other_docente)
    with pytest.raises(NotFound):
        ask(gen, "9.9")
    with pytest.raises(NotFound):
        list_wording_uc(world).execute(world.other_docente, world.process.id)

    assert jobs(world) == {}
    assert stored_draft(world) is None


def test_the_list_gives_the_newest_job_of_each_section(gen):
    world = gen.world
    add_activity(world)
    old = ask(gen, "1.3")
    finish(world, old)
    gen.clock.advance(minutes=5)
    new = ask(gen, "1.3")
    other = ask(gen, "2")

    listed = list_wording_uc(world).execute(world.docente, world.process.id)

    assert {key: job.id for key, job in listed.items()} == {"1.3": new.id, "2": other.id}
    assert listed["1.3"].state is GenerationState.GERANDO
