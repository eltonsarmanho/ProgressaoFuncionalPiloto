"""TAB-01, TAB-07, TAB-08, VER-04, VER-06, VER-07: asking for a generated document."""

import dataclasses

import pytest

from app.domain.entities.audit import AuditAction
from app.domain.entities.generated import (
    ARTIFACT_KINDS,
    DocumentKind,
    GeneratedDocument,
    GenerationCode,
    GenerationState,
)
from app.domain.entities.process import ProcessStatus
from app.domain.errors import Conflict, GenerationRefused, NotFound
from tests.integration.doc_usecases.generation_support import add_activity, build_request


def rows(world, process=None) -> list[GeneratedDocument]:
    with world.uow_factory() as uow:
        return list(uow.generations.list_for_process((process or world.process).id))


def refusal(request, world, kind=DocumentKind.TABELA) -> GenerationRefused:
    with pytest.raises(GenerationRefused) as error:
        request.execute(world.admin, world.process.id, kind)
    return error.value


@pytest.mark.parametrize("kind", list(ARTIFACT_KINDS))
def test_a_request_stores_a_generating_row_of_the_kind_for_the_actor(gen, kind):
    world = gen.world
    add_activity(world)

    generation = gen.request().execute(world.docente, world.process.id, kind)

    assert (generation.kind, generation.state) == (kind, GenerationState.GERANDO)
    assert (generation.version_number, generation.started_at) == (None, None)
    assert generation.requested_by == world.docente.id
    assert generation.requested_at == gen.clock.now()
    assert rows(world) == [generation]


def test_a_process_with_no_validated_activity_is_refused_and_no_row_is_created(gen):
    world = gen.world

    error = refusal(gen.request(), world)

    assert error.code == GenerationCode.SEM_ATIVIDADES_VALIDADAS
    assert rows(world) == []


def test_a_process_without_a_chosen_table_is_refused_and_no_row_is_created(docs):
    world = docs.world
    add_activity(world)

    error = refusal(build_request(world, docs), world)

    assert error.code == GenerationCode.TABELA_NAO_ESCOLHIDA
    assert rows(world) == []


def test_a_second_equal_request_while_one_is_generating_is_a_conflict(gen):
    world = gen.world
    add_activity(world)
    first = gen.request().execute(world.admin, world.process.id, DocumentKind.TABELA)

    with pytest.raises(Conflict) as error:
        gen.request().execute(world.admin, world.process.id, DocumentKind.TABELA)

    assert error.value.code == GenerationCode.GERACAO_EM_ANDAMENTO
    assert [r.id for r in rows(world)] == [first.id]


def test_requests_of_different_kinds_coexist(gen):
    world = gen.world
    add_activity(world)

    for kind in ARTIFACT_KINDS:
        gen.request().execute(world.admin, world.process.id, kind)

    assert sorted(r.kind for r in rows(world)) == sorted(ARTIFACT_KINDS)


def test_a_new_request_is_accepted_after_the_previous_one_failed(gen):
    world = gen.world
    add_activity(world)
    first = gen.request().execute(world.admin, world.process.id, DocumentKind.TABELA)
    with world.uow_factory() as uow:
        uow.generations.finish_failed(
            first.id, gen.clock.now(), GenerationCode.ERRO_INTERNO, "Erro"
        )
        uow.commit()

    second = gen.request().execute(world.admin, world.process.id, DocumentKind.TABELA)

    assert second.id != first.id
    assert second.state is GenerationState.GERANDO


@pytest.mark.parametrize("who", ["other_docente", "other_secretaria"])
def test_a_process_outside_the_access_of_the_actor_is_not_found(gen, who):
    world = gen.world
    add_activity(world)

    with pytest.raises(NotFound):
        gen.request().execute(
            getattr(world, who), world.process.id, DocumentKind.TABELA
        )

    assert rows(world) == []


def test_the_secretaria_of_the_unit_may_ask(gen):
    world = gen.world
    add_activity(world)

    generation = gen.request().execute(
        world.secretaria, world.process.id, DocumentKind.TABELA
    )

    assert generation.requested_by == world.secretaria.id


@pytest.mark.parametrize("status", [ProcessStatus.CONCLUIDO, ProcessStatus.ARQUIVADO])
def test_a_concluded_or_archived_process_still_generates(gen, status):
    world = gen.world
    add_activity(world)
    with world.uow_factory() as uow:
        current = uow.processes.get(world.process.id)
        uow.processes.update(dataclasses.replace(current, status=status), current.version)
        uow.commit()

    generation = gen.request().execute(world.admin, world.process.id, DocumentKind.TABELA)

    assert generation.state is GenerationState.GERANDO


def test_the_request_is_audited_with_the_kind_and_the_state_and_no_text(gen):
    world = gen.world
    add_activity(world, title="Orientação de Fulano")

    generation = gen.request().execute(
        world.admin, world.process.id, DocumentKind.RELATORIO
    )

    with world.uow_factory() as uow:
        [event] = uow.audit.list_for("generated_document", str(generation.id))
    assert event.action is AuditAction.CREATE
    assert event.user_id == world.admin.id
    assert event.changes == {
        "kind": {"before": None, "after": "RELATORIO"},
        "state": {"before": None, "after": "GERANDO"},
    }
