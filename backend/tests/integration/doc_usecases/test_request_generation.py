"""TAB-01, TAB-07, TAB-08, VER-04, VER-06, VER-07: asking for a generated document."""

import dataclasses

import pytest

from app.application.use_cases.generated_documents import RequestGeneration
from app.domain.entities.audit import AuditAction
from app.domain.entities.generated import (
    DocumentKind,
    GeneratedDocument,
    GenerationCode,
    GenerationState,
)
from app.domain.entities.process import ProcessStatus
from app.domain.errors import Conflict, GenerationRefused, NotFound
from tests.integration.doc_usecases.generation_support import FixedClock, add_activity


def request_use_case(world) -> RequestGeneration:
    return RequestGeneration(world.uow_factory, world.audit, world.policy, FixedClock())


def rows(world, process=None) -> list[GeneratedDocument]:
    with world.uow_factory() as uow:
        return list(uow.generations.list_for_process((process or world.process).id))


def refusal(world, kind=DocumentKind.TABELA, actor=None, process=None) -> GenerationRefused:
    with pytest.raises(GenerationRefused) as error:
        request_use_case(world).execute(
            actor or world.admin, (process or world.process).id, kind
        )
    return error.value


@pytest.mark.parametrize("kind", list(DocumentKind))
def test_a_request_stores_a_generating_row_of_the_kind_for_the_actor(official_chosen, kind):
    world = official_chosen
    add_activity(world)

    generation = request_use_case(world).execute(world.docente, world.process.id, kind)

    assert (generation.kind, generation.state) == (kind, GenerationState.GERANDO)
    assert (generation.version_number, generation.started_at) == (None, None)
    assert generation.requested_by == world.docente.id
    assert generation.requested_at == FixedClock().now()
    assert rows(world) == [generation]


def test_a_process_with_no_validated_activity_is_refused_and_no_row_is_created(official_chosen):
    world = official_chosen

    error = refusal(world)

    assert error.code == GenerationCode.SEM_ATIVIDADES_VALIDADAS
    assert rows(world) == []


def test_a_process_without_a_chosen_table_is_refused_and_no_row_is_created(world):
    add_activity(world)

    error = refusal(world)

    assert error.code == GenerationCode.TABELA_NAO_ESCOLHIDA
    assert rows(world) == []


def test_a_second_equal_request_while_one_is_generating_is_a_conflict(official_chosen):
    world = official_chosen
    add_activity(world)
    first = request_use_case(world).execute(world.admin, world.process.id, DocumentKind.TABELA)

    with pytest.raises(Conflict) as error:
        request_use_case(world).execute(world.admin, world.process.id, DocumentKind.TABELA)

    assert error.value.code == GenerationCode.GERACAO_EM_ANDAMENTO
    assert [r.id for r in rows(world)] == [first.id]


def test_requests_of_different_kinds_coexist(official_chosen):
    world = official_chosen
    add_activity(world)

    for kind in DocumentKind:
        request_use_case(world).execute(world.admin, world.process.id, kind)

    assert sorted(r.kind for r in rows(world)) == sorted(DocumentKind)


def test_a_new_request_is_accepted_after_the_previous_one_failed(official_chosen):
    world = official_chosen
    add_activity(world)
    first = request_use_case(world).execute(world.admin, world.process.id, DocumentKind.TABELA)
    with world.uow_factory() as uow:
        uow.generations.finish_failed(
            first.id, FixedClock().now(), GenerationCode.ERRO_INTERNO, "Erro"
        )
        uow.commit()

    second = request_use_case(world).execute(world.admin, world.process.id, DocumentKind.TABELA)

    assert second.id != first.id
    assert second.state is GenerationState.GERANDO


@pytest.mark.parametrize("who", ["other_docente", "other_secretaria"])
def test_a_process_outside_the_access_of_the_actor_is_not_found(official_chosen, who):
    world = official_chosen
    add_activity(world)

    with pytest.raises(NotFound):
        request_use_case(world).execute(
            getattr(world, who), world.process.id, DocumentKind.TABELA
        )

    assert rows(world) == []


def test_the_secretaria_of_the_unit_may_ask(official_chosen):
    world = official_chosen
    add_activity(world)

    generation = request_use_case(world).execute(
        world.secretaria, world.process.id, DocumentKind.TABELA
    )

    assert generation.requested_by == world.secretaria.id


@pytest.mark.parametrize("status", [ProcessStatus.CONCLUIDO, ProcessStatus.ARQUIVADO])
def test_a_concluded_or_archived_process_still_generates(official_chosen, status):
    world = official_chosen
    add_activity(world)
    with world.uow_factory() as uow:
        current = uow.processes.get(world.process.id)
        uow.processes.update(dataclasses.replace(current, status=status), current.version)
        uow.commit()

    generation = request_use_case(world).execute(world.admin, world.process.id, DocumentKind.TABELA)

    assert generation.state is GenerationState.GERANDO


def test_the_request_is_audited_with_the_kind_and_the_state_and_no_text(official_chosen):
    world = official_chosen
    add_activity(world, title="Orientação de Fulano")

    generation = request_use_case(world).execute(
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
