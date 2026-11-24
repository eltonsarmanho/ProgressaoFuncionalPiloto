"""DOS-02 to DOS-06, BNAV-02, BNAV-03: GetDossier and SetDossierDelivery (synthetic data only)."""

import pytest

from app.application.use_cases.dossier import GetDossier, SetDossierDelivery
from app.domain.entities.audit import AuditAction
from app.domain.entities.generated import DocumentKind, GenerationState
from app.domain.entities.process import ProcessStatus
from app.domain.errors import Conflict, NotFound, ValidationFailed
from app.domain.rules.dossier_checklist import ChecklistState
from app.infrastructure.documents.config_loader import load_dossier_order
from tests.integration.doc_usecases.board_support import add_typed_ordinance
from tests.integration.doc_usecases.conclusion_support import add_generation
from tests.integration.doc_usecases.draft_support import set_status
from tests.integration.documents.generated_support import T0, make_file, make_generation
from tests.integration.scoring.conftest import FixedClock

K = DocumentKind
S = ChecklistState
ENTITY = "dossier_delivery"
ORDER = [
    "REQUERIMENTO",
    "PORTARIA_ULTIMA_PROGRESSAO",
    "DECLARACAO_EXERCICIOS_ANTERIORES",
    "RELATORIO",
    "TABELA",
    "COMPROVANTE",
    "CURRICULO_LATTES",
    "PORTARIA_BANCA",
    "PARECER",
]


def get_uc(world) -> GetDossier:
    return GetDossier(world.uow_factory, world.audit, world.policy, load_dossier_order)


def set_uc(world) -> SetDossierDelivery:
    return SetDossierDelivery(
        world.uow_factory, world.audit, world.policy, load_dossier_order, FixedClock()
    )


def dossier(world, actor=None):
    return get_uc(world).execute(actor or world.docente, world.process.id)


def states(world, actor=None) -> dict:
    return {item.key: item.state for item in dossier(world, actor)}


def deliver(world, key, delivered=True, actor=None):
    return set_uc(world).execute(actor or world.docente, world.process.id, key, delivered)


def events(world):
    with world.uow_factory() as uow:
        return list(uow.audit.list_for(ENTITY, str(world.process.id)))


def add_table_generation(world, version_id):
    """A ready Tabela whose snapshot says it was made with the table version `version_id`."""
    generation = make_generation(world.process, world.admin.id, K.TABELA)
    with world.uow_factory() as uow:
        uow.generations.add(generation)
        uow.generations.finish_ready(
            generation.id,
            T0,
            [make_file()],
            {"total": "1", "table_version": {"id": str(version_id)}},
            (),
        )
        uow.commit()
    return generation


def add_three_ready(world):
    return {kind: add_generation(world, kind) for kind in (K.TABELA, K.RELATORIO, K.COMPROVANTE)}


# --- GetDossier: DOS-01, DOS-02, DOS-05 -------------------------------------------------------


def test_a_process_with_only_the_three_documents_ready_has_three_generated_and_six_pending(world):
    add_three_ready(world)

    items = dossier(world)

    assert [item.key for item in items] == ORDER
    assert [item.order for item in items] == list(range(1, 10))
    assert {item.key for item in items if item.state is S.GERADO} == {
        "RELATORIO",
        "TABELA",
        "COMPROVANTE",
    }
    assert sorted(item.key for item in items if item.state is S.PENDENTE) == sorted(
        set(ORDER) - {"RELATORIO", "TABELA", "COMPROVANTE"}
    )


def test_a_generated_item_carries_the_last_ready_version_number_and_its_id(world):
    first = add_generation(world, K.RELATORIO)
    second = add_generation(world, K.RELATORIO)
    add_generation(world, K.RELATORIO, GenerationState.FALHOU)

    item = next(i for i in dossier(world) if i.key == "RELATORIO")

    assert item.state is S.GERADO
    assert item.version_number == 2
    assert item.generation_id == second.id != first.id


def test_a_process_with_nothing_has_every_item_pending_and_no_version(world):
    items = dossier(world)

    assert {item.state for item in items} == {S.PENDENTE}
    assert {(item.version_number, item.generation_id) for item in items} == {(None, None)}


def test_the_parecer_and_the_requerimento_ready_show_as_generated(world):
    add_generation(world, K.REQUERIMENTO)
    add_generation(world, K.PARECER)

    result = states(world)

    assert result["REQUERIMENTO"] is S.GERADO
    assert result["PARECER"] is S.GERADO


# --- GetDossier: DOS-03 -----------------------------------------------------------------------


def test_the_ordinance_with_a_member_shows_as_registered(world):
    add_typed_ordinance(world)

    assert states(world)["PORTARIA_BANCA"] is S.REGISTRADA


def test_an_ordinance_without_members_is_still_pending(world):
    add_typed_ordinance(world, members=())

    assert states(world)["PORTARIA_BANCA"] is S.PENDENTE


# --- GetDossier: DOS-06 -----------------------------------------------------------------------


def test_a_tabela_made_with_another_version_of_the_table_is_outdated_until_that_one_is_chosen(
    world,
):
    world.choose.execute(world.admin, world.process.id, world.official_version.id, None, None)
    add_table_generation(world, world.other_version.id)

    item = next(i for i in dossier(world) if i.key == "TABELA")
    assert (item.state, item.outdated_table) == (S.GERADO, True)

    world.choose.execute(world.admin, world.process.id, world.other_version.id, None, None)
    item = next(i for i in dossier(world) if i.key == "TABELA")
    assert (item.state, item.outdated_table) == (S.GERADO, False)


def test_a_tabela_made_with_the_chosen_version_is_not_outdated(world):
    world.choose.execute(world.admin, world.process.id, world.official_version.id, None, None)
    add_table_generation(world, world.official_version.id)

    item = next(i for i in dossier(world) if i.key == "TABELA")

    assert item.outdated_table is False


# --- SetDossierDelivery: DOS-04 ---------------------------------------------------------------


def test_marking_the_lattes_shows_it_delivered_on_reload_and_audits_without_justification(world):
    result = deliver(world, "CURRICULO_LATTES")

    assert next(i for i in result if i.key == "CURRICULO_LATTES").state is S.ENTREGUE
    assert states(world)["CURRICULO_LATTES"] is S.ENTREGUE
    with world.uow_factory() as uow:
        assert uow.dossier_deliveries.keys(world.process.id) == {"CURRICULO_LATTES"}
    [event] = events(world)
    assert event.action is AuditAction.UPDATE
    assert event.user_id == world.docente.id
    assert event.justification is None
    assert event.changes["delivered"] == {"before": False, "after": True}
    assert event.changes["item_key"]["after"] == "CURRICULO_LATTES"


def test_marking_again_changes_nothing_and_writes_no_event(world):
    deliver(world, "CURRICULO_LATTES")

    result = deliver(world, "CURRICULO_LATTES")

    assert next(i for i in result if i.key == "CURRICULO_LATTES").state is S.ENTREGUE
    assert len(events(world)) == 1


def test_unmarking_goes_back_to_pending_and_audits(world):
    deliver(world, "CURRICULO_LATTES")

    result = deliver(world, "CURRICULO_LATTES", False)

    assert next(i for i in result if i.key == "CURRICULO_LATTES").state is S.PENDENTE
    assert states(world)["CURRICULO_LATTES"] is S.PENDENTE
    mark, unmark = events(world)
    assert unmark.changes["delivered"] == {"before": True, "after": False}
    assert unmark.changes["item_key"]["before"] == "CURRICULO_LATTES"
    assert unmark.justification is None
    assert mark.changes["delivered"]["after"] is True


def test_unmarking_what_was_never_marked_writes_no_event(world):
    result = deliver(world, "CURRICULO_LATTES", False)

    assert next(i for i in result if i.key == "CURRICULO_LATTES").state is S.PENDENTE
    assert events(world) == []


def test_the_marks_of_the_three_manual_items_are_independent(world):
    deliver(world, "PORTARIA_ULTIMA_PROGRESSAO")
    deliver(world, "DECLARACAO_EXERCICIOS_ANTERIORES")

    result = states(world)

    assert result["PORTARIA_ULTIMA_PROGRESSAO"] is S.ENTREGUE
    assert result["DECLARACAO_EXERCICIOS_ANTERIORES"] is S.ENTREGUE
    assert result["CURRICULO_LATTES"] is S.PENDENTE


@pytest.mark.parametrize("key", ["TABELA", "PORTARIA_BANCA", "REQUERIMENTO", "NAO_EXISTE", ""])
def test_a_key_that_is_not_manual_or_does_not_exist_is_a_422_and_stores_nothing(world, key):
    with pytest.raises(ValidationFailed) as raised:
        deliver(world, key)

    assert raised.value.field == "key"
    with world.uow_factory() as uow:
        assert uow.dossier_deliveries.keys(world.process.id) == set()
    assert events(world) == []


def test_marking_does_not_make_a_generated_item_delivered(world):
    deliver(world, "CURRICULO_LATTES")

    assert states(world)["TABELA"] is S.PENDENTE


# --- BNAV-02 ----------------------------------------------------------------------------------


@pytest.mark.parametrize("status", [ProcessStatus.CONCLUIDO, ProcessStatus.ARQUIVADO])
def test_a_closed_process_refuses_the_mark_and_the_unmark_but_still_reads(world, status):
    deliver(world, "CURRICULO_LATTES")
    set_status(world, status)

    for key, delivered in (("PORTARIA_ULTIMA_PROGRESSAO", True), ("CURRICULO_LATTES", False)):
        with pytest.raises(Conflict) as raised:
            deliver(world, key, delivered)
        assert raised.value.code == "PROCESSO_SOMENTE_LEITURA"

    assert states(world)["CURRICULO_LATTES"] is S.ENTREGUE
    assert states(world)["PORTARIA_ULTIMA_PROGRESSAO"] is S.PENDENTE
    assert len(events(world)) == 1


# --- BNAV-03 ----------------------------------------------------------------------------------


@pytest.mark.parametrize("who", ["other_docente", "other_secretaria"])
def test_someone_without_access_gets_not_found_on_the_read_and_on_the_mark(world, who):
    actor = getattr(world, who)

    with pytest.raises(NotFound):
        dossier(world, actor)
    with pytest.raises(NotFound):
        deliver(world, "CURRICULO_LATTES", actor=actor)

    with world.uow_factory() as uow:
        assert uow.dossier_deliveries.keys(world.process.id) == set()


@pytest.mark.parametrize("who", ["admin", "docente", "secretaria"])
def test_admin_owner_and_the_secretary_of_the_unit_read_and_mark(world, who):
    actor = getattr(world, who)

    result = deliver(world, "CURRICULO_LATTES", actor=actor)

    assert next(i for i in result if i.key == "CURRICULO_LATTES").state is S.ENTREGUE
    assert events(world)[-1].user_id == actor.id
