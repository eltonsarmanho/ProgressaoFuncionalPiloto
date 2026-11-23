"""PAR-07 to PAR-10, PAR-12, PMOD-22, PMOD-23, REQ-01, BNAV-02, BNAV-03: asking for a Parecer or a
Requerimento."""

import dataclasses
from decimal import Decimal

import pytest

from app.application.use_cases.generated_documents import GenerationLimits
from app.application.use_cases.scoring import compute_process_score
from app.domain.entities.audit import AuditAction
from app.domain.entities.board import BoardMember, BoardRole, OpinionConclusion, ValueSource
from app.domain.entities.generated import (
    DocumentKind,
    GenerationCode,
    GenerationState,
)
from app.domain.entities.process import ProcessStatus
from app.domain.errors import Conflict, GenerationRefused, NotFound
from tests.integration.doc_usecases.board_support import add_typed_ordinance
from tests.integration.doc_usecases.generation_support import add_activity, build_request
from tests.integration.doc_usecases.opinion_support import (
    add_opinion,
    ask,
    craft_ready_table,
    ready_table,
)
from tests.integration.doc_usecases.test_request_refusals import FreeSpace
from tests.integration.scoring.conftest import choose_legacy_version

OUTDATED_MESSAGE = "A pontuação mudou depois da última Tabela; gere a Tabela de novo"
MB = 1024 * 1024


def rows(world, kind=None):
    with world.uow_factory() as uow:
        return list(uow.generations.list_for_process(world.process.id, kind))


def refusal(gen, kind, **kwargs) -> GenerationRefused:
    with pytest.raises(GenerationRefused) as error:
        ask(gen, kind, **kwargs)
    return error.value


def set_status(world, status):
    with world.uow_factory() as uow:
        current = uow.processes.get(world.process.id)
        uow.processes.update(dataclasses.replace(current, status=status), current.version)
        uow.commit()


def a_complete_board(gen):
    """A Tabela `PRONTO`, a board with three members and the conclusion chosen."""
    ready_table(gen)
    add_typed_ordinance(gen.world)
    add_opinion(gen.world)


# --- the order of the refusals of the Parecer (PAR-07 to PAR-10) -----------------------------


def test_no_conclusion_is_refused_even_with_no_members_and_no_table(gen):
    error = refusal(gen, DocumentKind.PARECER)

    assert error.code == GenerationCode.CONCLUSAO_AUSENTE
    assert rows(gen.world) == []


def test_an_opinion_saved_without_a_conclusion_is_still_refused_for_it(gen):
    add_opinion(gen.world, conclusion=None)

    assert refusal(gen, DocumentKind.PARECER).code == GenerationCode.CONCLUSAO_AUSENTE


def test_a_conclusion_and_no_members_is_refused_for_the_board(gen):
    add_opinion(gen.world)

    error = refusal(gen, DocumentKind.PARECER)

    assert error.code == GenerationCode.BANCA_SEM_MEMBROS
    assert rows(gen.world) == []


def test_an_ordinance_with_no_member_is_the_same_as_no_ordinance(gen):
    add_opinion(gen.world)
    add_typed_ordinance(gen.world, members=())

    assert refusal(gen, DocumentKind.PARECER).code == GenerationCode.BANCA_SEM_MEMBROS


def alternate(name="Davi Suplente Rocha") -> BoardMember:
    return BoardMember(name, BoardRole.SUPLENTE, 1, ValueSource.INFORMADO)


def titular(name="Bruno Membro Lima") -> BoardMember:
    return BoardMember(name, BoardRole.MEMBRO, 1, ValueSource.INFORMADO)


def test_an_ordinance_with_only_alternates_is_refused_for_the_board_even_with_everything_else(gen):
    ready_table(gen)
    add_opinion(gen.world)
    add_typed_ordinance(gen.world, members=(alternate(), alternate("Eva Suplente Dias")))

    error = refusal(gen, DocumentKind.PARECER)

    assert error.code == GenerationCode.BANCA_SEM_MEMBROS
    assert [r.kind for r in rows(gen.world)] == [DocumentKind.TABELA]


def test_only_alternates_and_no_conclusion_is_refused_for_the_conclusion_first(gen):
    add_opinion(gen.world, conclusion=None)
    add_typed_ordinance(gen.world, members=(alternate(),))

    assert refusal(gen, DocumentKind.PARECER).code == GenerationCode.CONCLUSAO_AUSENTE


def test_only_alternates_and_no_table_is_refused_for_the_board_before_the_table(gen):
    add_opinion(gen.world)
    add_typed_ordinance(gen.world, members=(alternate(),))

    assert refusal(gen, DocumentKind.PARECER).code == GenerationCode.BANCA_SEM_MEMBROS


def test_an_ordinance_with_an_alternate_and_one_member_is_accepted(gen):
    ready_table(gen)
    add_opinion(gen.world)
    add_typed_ordinance(gen.world, members=(alternate(), titular()))

    assert ask(gen, DocumentKind.PARECER).state is GenerationState.GERANDO


def test_an_ordinance_with_only_a_president_is_accepted(gen):
    ready_table(gen)
    add_opinion(gen.world)
    president = BoardMember("Ana Presidente Souza", BoardRole.PRESIDENTE, 1, ValueSource.INFORMADO)
    add_typed_ordinance(gen.world, members=(president,))

    assert ask(gen, DocumentKind.PARECER).state is GenerationState.GERANDO


def test_members_and_no_ready_table_is_refused_for_the_table(gen):
    add_opinion(gen.world)
    add_typed_ordinance(gen.world)

    error = refusal(gen, DocumentKind.PARECER)

    assert error.code == GenerationCode.TABELA_AUSENTE
    assert rows(gen.world) == []


def test_a_table_that_is_only_generating_does_not_count_as_ready(gen):
    add_activity(gen.world)
    ask(gen, DocumentKind.TABELA)  # GERANDO, never run
    add_opinion(gen.world)
    add_typed_ordinance(gen.world)

    assert refusal(gen, DocumentKind.PARECER).code == GenerationCode.TABELA_AUSENTE


def test_an_activity_that_changes_the_total_after_the_table_is_refused_as_outdated(gen):
    a_complete_board(gen)
    add_activity(gen.world, title="Outra orientação depois da Tabela")

    error = refusal(gen, DocumentKind.PARECER)

    assert error.code == GenerationCode.TABELA_DESATUALIZADA
    assert OUTDATED_MESSAGE in error.message
    assert [r.kind for r in rows(gen.world)] == [DocumentKind.TABELA]


def test_the_same_total_with_another_table_version_is_also_outdated(gen):
    a_complete_board(gen)
    with gen.world.uow_factory() as uow:
        chosen = uow.generations.latest_ready_by_kind(gen.world.process.id)[DocumentKind.TABELA]
    choose_legacy_version(gen.world)
    with gen.world.uow_factory() as uow:
        now = compute_process_score(uow, uow.processes.get(gen.world.process.id))
    # the premise: the total did not move, only the version did
    assert Decimal(chosen.snapshot["total"]) == now.result.total
    assert str(now.chosen.version.id) != chosen.snapshot["table_version"]["id"]

    error = refusal(gen, DocumentKind.PARECER)

    assert error.code == GenerationCode.TABELA_DESATUALIZADA


# --- accepted ---------------------------------------------------------------------------------


def test_everything_in_order_stores_a_generating_row_of_the_parecer_and_audits_it(gen):
    a_complete_board(gen)

    generation = ask(gen, DocumentKind.PARECER, actor=gen.world.docente)

    assert (generation.kind, generation.state) == (DocumentKind.PARECER, GenerationState.GERANDO)
    assert generation.requested_by == gen.world.docente.id
    assert rows(gen.world, DocumentKind.PARECER) == [generation]
    with gen.world.uow_factory() as uow:
        [event] = uow.audit.list_for("generated_document", str(generation.id))
    assert event.action is AuditAction.CREATE
    assert event.changes == {
        "kind": {"before": None, "after": "PARECER"},
        "state": {"before": None, "after": "GERANDO"},
    }


@pytest.mark.parametrize("conclusion", list(OpinionConclusion))
def test_either_conclusion_is_accepted(gen, conclusion):
    ready_table(gen)
    add_typed_ordinance(gen.world)
    add_opinion(gen.world, conclusion=conclusion)

    assert ask(gen, DocumentKind.PARECER).state is GenerationState.GERANDO


def test_the_parecer_needs_neither_a_validated_activity_nor_a_chosen_table(docs):
    # a Tabela PRONTO of a total of zero from the time there was nothing to count: PAR-10 compares
    # only that Tabela with the calculation of now, so no activity and no table is no refusal
    world = docs.world
    craft_ready_table(
        world, docs.clock, {"total": "0.00", "subtotals": {}, "table_version": {"id": None}}
    )
    add_typed_ordinance(world)
    add_opinion(world)

    generation = build_request(world, docs).execute(
        world.admin, world.process.id, DocumentKind.PARECER
    )

    assert generation.state is GenerationState.GERANDO


# --- the Requerimento -------------------------------------------------------------------------


def test_the_requerimento_is_accepted_with_no_activity_no_table_and_no_other_generation(docs):
    world = docs.world

    generation = build_request(world, docs).execute(
        world.docente, world.process.id, DocumentKind.REQUERIMENTO
    )

    assert (generation.kind, generation.state) == (
        DocumentKind.REQUERIMENTO,
        GenerationState.GERANDO,
    )
    assert rows(world) == [generation]


def test_the_requerimento_is_audited_with_the_kind_and_the_state(gen):
    generation = ask(gen, DocumentKind.REQUERIMENTO)

    with gen.world.uow_factory() as uow:
        [event] = uow.audit.list_for("generated_document", str(generation.id))
    assert event.changes == {
        "kind": {"before": None, "after": "REQUERIMENTO"},
        "state": {"before": None, "after": "GERANDO"},
    }


# --- read-only process (BNAV-02), both sides of DEL-13 ----------------------------------------


@pytest.mark.parametrize("status", [ProcessStatus.CONCLUIDO, ProcessStatus.ARQUIVADO])
def test_a_read_only_process_refuses_the_two_new_kinds_and_still_generates_the_others(gen, status):
    a_complete_board(gen)
    set_status(gen.world, status)

    for kind in (DocumentKind.PARECER, DocumentKind.REQUERIMENTO):
        with pytest.raises(Conflict) as error:
            ask(gen, kind)
        assert error.value.code == GenerationCode.PROCESSO_SOMENTE_LEITURA
    assert [r.kind for r in rows(gen.world)] == [DocumentKind.TABELA]
    for kind in (DocumentKind.TABELA, DocumentKind.RELATORIO):
        assert ask(gen, kind).state is GenerationState.GERANDO


# --- one at a time, access, space --------------------------------------------------------------


@pytest.mark.parametrize("kind", [DocumentKind.PARECER, DocumentKind.REQUERIMENTO])
def test_a_second_request_of_the_same_kind_while_one_is_generating_is_a_conflict(gen, kind):
    a_complete_board(gen)
    first = ask(gen, kind)

    with pytest.raises(Conflict) as error:
        ask(gen, kind)

    assert error.value.code == GenerationCode.GERACAO_EM_ANDAMENTO
    assert [r.id for r in rows(gen.world, kind)] == [first.id]


def test_the_two_new_kinds_coexist_with_each_other_and_with_the_table(gen):
    a_complete_board(gen)

    for kind in (DocumentKind.PARECER, DocumentKind.REQUERIMENTO, DocumentKind.TABELA):
        assert ask(gen, kind).state is GenerationState.GERANDO

    assert sorted(r.kind for r in rows(gen.world, None) if r.state is GenerationState.GERANDO) == (
        sorted([DocumentKind.PARECER, DocumentKind.REQUERIMENTO, DocumentKind.TABELA])
    )


@pytest.mark.parametrize("kind", [DocumentKind.PARECER, DocumentKind.REQUERIMENTO])
@pytest.mark.parametrize("who", ["other_docente", "other_secretaria"])
def test_a_process_outside_the_access_of_the_actor_is_not_found(gen, kind, who):
    a_complete_board(gen)

    with pytest.raises(NotFound):
        ask(gen, kind, actor=getattr(gen.world, who))

    assert [r.kind for r in rows(gen.world)] == [DocumentKind.TABELA]


@pytest.mark.parametrize("kind", [DocumentKind.PARECER, DocumentKind.REQUERIMENTO])
def test_less_than_the_minimum_free_space_refuses_the_two_new_kinds(gen, kind):
    a_complete_board(gen)
    limits = GenerationLimits(min_free_bytes=200 * MB)

    with pytest.raises(GenerationRefused) as error:
        gen.request(storage=FreeSpace(200 * MB - 1), limits=limits).execute(
            gen.world.admin, gen.world.process.id, kind
        )

    assert error.value.code == GenerationCode.ESPACO_INSUFICIENTE
    assert rows(gen.world, kind) == []
