"""ARR-02 to ARR-07: saving the arrangement of the Comprovante."""

import uuid

import pytest

from app.application.services.generation_inputs import load_generation_inputs
from app.domain.entities.activity import ActivityStatus
from app.domain.entities.audit import AuditAction
from app.domain.entities.comprovante import EvidenceKey, LayoutActivity, LayoutPage
from app.domain.entities.generated import GenerationCode
from app.domain.entities.process import ProcessStatus
from app.domain.errors import Conflict, GenerationRefused, NotFound, StaleVersion, ValidationFailed
from app.domain.rules.comprovante_plan import plan_comprovante
from tests.integration.doc_usecases.draft_support import (
    get_layout_uc,
    save_layout_uc,
    set_status,
)
from tests.integration.doc_usecases.generation_support import (
    add_activity,
    add_document,
    link,
    link_pages,
)

TOC_CAPACITY = 40


def entry(activity, *pages, **kwargs):
    return LayoutActivity(activity.id, tuple(LayoutPage(d.id, n) for d, n in pages), **kwargs)


def save(world, activities, version=0, actor=None):
    return save_layout_uc(world).execute(
        actor or world.docente, world.process.id, version, activities
    )


def stored(world):
    with world.uow_factory() as uow:
        return uow.comprovante_layouts.get(world.process.id)


def in_force(world):
    """The arrangement the generation uses and the plan it numbers from."""
    with world.uow_factory() as uow:
        inputs = load_generation_inputs(uow, uow.processes.get(world.process.id))
    return inputs.layout, plan_comprovante(inputs.layout, inputs.activities, TOC_CAPACITY)


def links(world, activity):
    with world.uow_factory() as uow:
        return sorted(
            (e.document_id, e.page_number) for e in uow.evidences.list_for_activity(activity.id)
        )


def pages(layout, activity):
    found = next(a for a in layout.activities if a.activity_id == activity.id)
    return [(p.document_id, p.page) for p in found.pages]


def test_adding_a_page_in_the_requested_position_is_kept_and_the_generation_uses_it(
    official_chosen,
):
    world = official_chosen
    activity = add_activity(world)
    document = add_document(world, page_count=6)
    link(world, activity, document, 1)

    saved = save(world, [entry(activity, (document, 4), (document, 1))])

    assert saved.version == 1
    assert pages(stored(world), activity) == [(document.id, 4), (document.id, 1)]
    layout, plan = in_force(world)
    assert pages(layout, activity) == [(document.id, 4), (document.id, 1)]
    assert [p.source_page for p in plan.pages if p.document_id] == [4, 1]
    assert links(world, activity) == [(document.id, 1)]  # no link was created


def test_removing_a_page_leaves_it_out_of_the_comprovante_and_keeps_the_link(official_chosen):
    world = official_chosen
    activity = add_activity(world)
    document = add_document(world, page_count=4)
    link_pages(world, activity, document, [1, 2, 3])

    save(world, [entry(activity, (document, 1), (document, 3))])

    layout, plan = in_force(world)
    assert pages(layout, activity) == [(document.id, 1), (document.id, 3)]
    assert [p.source_page for p in plan.pages if p.document_id] == [1, 3]
    assert links(world, activity) == [(document.id, 1), (document.id, 2), (document.id, 3)]


def test_reordering_activities_inside_an_item_and_pages_inside_an_activity_is_kept(
    official_chosen,
):
    world = official_chosen
    first = add_activity(world, title="Primeira orientação")
    second = add_activity(world, title="Segunda orientação")
    document = add_document(world, page_count=4)
    link_pages(world, first, document, [1, 2])
    link_pages(world, second, document, [3])

    save(world, [entry(second, (document, 3)), entry(first, (document, 2), (document, 1))])

    layout, plan = in_force(world)
    assert [a.activity_id for a in layout.activities] == [second.id, first.id]
    assert pages(layout, first) == [(document.id, 2), (document.id, 1)]
    assert [p.source_page for p in plan.pages if p.document_id] == [3, 2, 1]


def test_the_saved_arrangement_reads_back_as_saved_and_not_stale(official_chosen):
    world = official_chosen
    activity = add_activity(world)
    document = add_document(world)
    link(world, activity, document, 1)

    save(world, [entry(activity, (document, 1))])
    view = get_layout_uc(world).execute(world.docente, world.process.id)

    assert (view.saved, view.layout.version, view.stale) == (True, 1, False)


def test_the_links_the_arrangement_was_built_from_are_stored_and_a_later_link_makes_it_stale(
    official_chosen,
):
    world = official_chosen
    activity = add_activity(world)
    document = add_document(world, page_count=3)
    link(world, activity, document, 1)

    saved = save(world, [entry(activity, (document, 1))])

    assert saved.base_evidence_keys == (EvidenceKey(activity.id, document.id, 1),)
    assert stored(world).base_evidence_keys == saved.base_evidence_keys
    link(world, activity, document, 2)
    assert get_layout_uc(world).execute(world.docente, world.process.id).stale is True


def test_a_document_that_is_not_of_the_process_is_not_found_and_nothing_is_saved(
    official_chosen, add_process
):
    world = official_chosen
    activity = add_activity(world)
    foreign = add_document(world, add_process())

    for page_document in (foreign, type("X", (), {"id": uuid.uuid4()})()):
        with pytest.raises(NotFound):
            save(world, [entry(activity, (page_document, 1))])

    assert stored(world) is None


def test_a_page_past_the_end_of_the_document_is_refused(official_chosen):
    world = official_chosen
    activity = add_activity(world)
    document = add_document(world, page_count=2)

    with pytest.raises(GenerationRefused) as error:
        save(world, [entry(activity, (document, 3))])

    assert error.value.code == GenerationCode.PAGINA_FORA_DO_DOCUMENTO
    assert stored(world) is None


def test_a_page_of_a_document_outside_the_interstice_is_not_found(official_chosen):
    world = official_chosen
    activity = add_activity(world)
    outside = add_document(world, outside=True)

    with pytest.raises(NotFound):
        save(world, [entry(activity, (outside, 1))])

    assert stored(world) is None


def test_an_activity_that_is_not_validated_or_does_not_exist_is_not_found(official_chosen):
    world = official_chosen
    rejected = add_activity(world, status=ActivityStatus.REJEITADA)

    with pytest.raises(NotFound):
        save(world, [LayoutActivity(rejected.id)])
    with pytest.raises(NotFound):
        save(world, [LayoutActivity(uuid.uuid4())])

    assert stored(world) is None


def test_moving_an_activity_to_another_item_is_refused(official_chosen):
    world = official_chosen
    first = add_activity(world, title="Item 7", item_number=7)
    second = add_activity(world, title="Item 8", item_number=8)

    with pytest.raises(ValidationFailed):  # the item it was sent with is not the scoring's
        save(world, [entry(first, group_number=2, item_number=8), entry(second)])
    with pytest.raises(ValidationFailed):  # placed before the activities of the previous item
        save(world, [entry(second), entry(first)])

    assert stored(world) is None


def test_an_outdated_version_is_a_409_and_the_newer_arrangement_is_not_overwritten(
    official_chosen,
):
    world = official_chosen
    first = add_activity(world, title="Primeira")
    second = add_activity(world, title="Segunda")
    document = add_document(world, page_count=3)
    link_pages(world, first, document, [1])
    link_pages(world, second, document, [2])
    newer = save(world, [entry(first, (document, 1)), entry(second, (document, 2))])

    with pytest.raises(StaleVersion) as error:
        save(world, [entry(second, (document, 2)), entry(first, (document, 1))], version=0)

    assert error.value.code == GenerationCode.VERSAO_DESATUALIZADA
    assert stored(world) == newer
    again = save(world, [entry(second, (document, 2)), entry(first, (document, 1))], version=1)
    assert again.version == 2
    with pytest.raises(StaleVersion):
        save(world, [entry(first)], version=1)
    assert stored(world) == again


@pytest.mark.parametrize("status", [ProcessStatus.CONCLUIDO, ProcessStatus.ARQUIVADO])
def test_a_concluded_or_archived_process_refuses_the_save(official_chosen, status):
    world = official_chosen
    activity = add_activity(world)
    set_status(world, status)

    with pytest.raises(Conflict) as error:
        save(world, [entry(activity)])

    assert error.value.code == GenerationCode.PROCESSO_SOMENTE_LEITURA
    assert stored(world) is None


def test_a_process_out_of_reach_is_not_found(official_chosen):
    world = official_chosen
    activity = add_activity(world)

    with pytest.raises(NotFound):
        save(world, [entry(activity)], actor=world.other_docente)

    assert stored(world) is None


def test_the_audit_of_a_save_has_only_counts_and_the_version(official_chosen):
    world = official_chosen
    activity = add_activity(world, title="Título que não vai para a auditoria")
    document = add_document(world, original_name="nome-do-arquivo.pdf", page_count=3)
    link_pages(world, activity, document, [1, 2])
    save(world, [entry(activity, (document, 1), (document, 2))])

    with world.uow_factory() as uow:
        [event] = uow.audit.list_for("comprovante_layout", str(world.process.id))

    assert event.action is AuditAction.CREATE
    assert event.user_id == world.docente.id
    assert {k: v["after"] for k, v in event.changes.items()} == {
        "version": 1,
        "activities": 1,
        "pages": 2,
    }
    assert "nome-do-arquivo" not in str(event.changes)
    assert "Título" not in str(event.changes)
