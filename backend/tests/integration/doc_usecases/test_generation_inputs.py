"""TAB-01, TAB-02, UIG-06: what the generation reads from the process, in one read."""

from sqlalchemy import text

from app.application.services.generation_inputs import load_generation_inputs
from app.application.use_cases.scoring import compute_process_score
from app.domain.entities.activity import ActivityStatus
from app.domain.entities.comprovante import (
    ComprovanteLayout,
    EvidenceKey,
    LayoutActivity,
    LayoutPage,
)
from app.domain.rules.comprovante_plan import plan_comprovante
from tests.integration.doc_usecases.generation_support import (
    MOMENT,
    add_activity,
    add_document,
    link,
)

TOC_CAPACITY = 40


def load(world):
    with world.uow_factory() as uow:
        return load_generation_inputs(uow, uow.processes.get(world.process.id))


def test_only_validated_activities_with_group_and_item_go_in_and_the_rest_is_counted_by_reason(
    official_chosen,
):
    world = official_chosen
    kept = add_activity(world, title="Orientação")
    add_activity(world, title="Sugerida 1", status=ActivityStatus.AGUARDANDO_REVISAO)
    add_activity(world, title="Sugerida 2", status=ActivityStatus.AGUARDANDO_REVISAO)
    add_activity(world, title="Recusada", status=ActivityStatus.REJEITADA)
    add_activity(world, title="Sem item", group_number=None, item_number=None)

    inputs = load(world)

    assert [a.id for a in inputs.activities] == [kept.id]
    assert inputs.excluded == {"pendentes": 2, "rejeitadas": 1, "sem_enquadramento": 1}


def test_activities_come_in_the_order_of_the_table(official_chosen):
    world = official_chosen
    late = add_activity(world, title="Banca", group_number=3, item_number=2)
    second = add_activity(world, title="Segunda", item_number=7)
    first = add_activity(world, title="Primeira", item_number=3)

    inputs = load(world)

    assert [a.id for a in inputs.activities] == [first.id, second.id, late.id]


def test_the_score_is_the_one_of_compute_process_score_and_the_table_is_the_chosen_one(
    official_chosen,
):
    world = official_chosen
    add_activity(world, title="Orientação", quantity=4)

    inputs = load(world)
    with world.uow_factory() as uow:
        expected = compute_process_score(uow, uow.processes.get(world.process.id))

    assert inputs.score == expected
    assert inputs.score.result.counters.activities == 1
    assert inputs.version.id == world.official_version.id


def test_it_reads_the_professor_the_unit_and_the_process_for_the_header(official_chosen):
    world = official_chosen

    inputs = load(world)

    assert inputs.professor.id == world.professor.id
    assert inputs.unit.id == world.fasi.id
    assert inputs.process.id == world.process.id
    header = inputs.header
    assert (header.professor_name, header.unit_name) == (world.professor.full_name, world.fasi.name)
    assert (header.current_class, header.current_level) == ("C", 4)
    assert (header.target_class, header.target_level) == ("D", 1)
    assert (header.interstice.start.isoformat(), header.interstice.end.isoformat()) == (
        "2022-11-23",
        "2024-11-23",
    )


def test_it_reads_the_page_links_of_the_listed_activities_and_the_documents(official_chosen):
    world = official_chosen
    activity = add_activity(world)
    hidden = add_activity(world, status=ActivityStatus.REJEITADA)
    document = add_document(world, original_name="declaracao.pdf", page_count=3)
    kept = link(world, activity, document, 2)
    link(world, hidden, document, 1)

    inputs = load(world)

    assert [(e.activity_id, e.document_id, e.page_number) for e in inputs.evidences] == [
        (activity.id, document.id, 2)
    ]
    assert kept.id in [e.id for e in inputs.evidences]
    [found] = inputs.documents
    assert (found.id, found.original_name, found.page_count, found.mime) == (
        document.id,
        "declaracao.pdf",
        3,
        "application/pdf",
    )
    assert found.internal_name == document.internal_name
    assert found.file_deleted_at is None


def test_a_document_outside_the_interstice_is_in_no_input_and_no_page_of_it_is_planned(
    official_chosen,
):
    world = official_chosen
    activity = add_activity(world)
    inside = add_document(world)
    outside = add_document(world, outside=True)
    link(world, activity, inside, 1)
    link(world, activity, outside, 1)

    inputs = load(world)
    plan = plan_comprovante(inputs.layout, inputs.activities, TOC_CAPACITY)

    assert [d.id for d in inputs.documents] == [inside.id]
    assert [e.document_id for e in inputs.evidences] == [inside.id]
    attached = [p.document_id for p in plan.pages if p.document_id is not None]
    assert attached == [inside.id]
    assert outside.id not in {r.document_id for e in plan.toc for r in e.sources}


def test_pages_of_a_document_outside_the_interstice_leave_a_saved_layout(official_chosen):
    world = official_chosen
    activity = add_activity(world)
    inside = add_document(world)
    outside = add_document(world, outside=True)
    saved = ComprovanteLayout(
        world.process.id,
        (
            LayoutActivity(
                activity.id,
                (LayoutPage(outside.id, 1), LayoutPage(inside.id, 2)),
                group_number=2,
                item_number=7,
            ),
        ),
        (EvidenceKey(activity.id, outside.id, 1), EvidenceKey(activity.id, inside.id, 2)),
    )
    with world.uow_factory() as uow:
        uow.comprovante_layouts.create(saved, world.admin.id, 0)
        uow.commit()

    inputs = load(world)
    plan = plan_comprovante(inputs.layout, inputs.activities, TOC_CAPACITY)

    assert [(p.document_id, p.page) for p in inputs.layout.activities[0].pages] == [(inside.id, 2)]
    assert [(p.document_id, p.source_page) for p in plan.pages if p.document_id] == [(inside.id, 2)]


def test_a_saved_layout_wins_over_the_derived_one(official_chosen):
    world = official_chosen
    first = add_activity(world, title="Primeira", item_number=7)
    second = add_activity(world, title="Segunda", item_number=7)
    document = add_document(world)
    link(world, first, document, 1)
    link(world, second, document, 2)
    saved = ComprovanteLayout(
        world.process.id,
        (
            LayoutActivity(second.id, (LayoutPage(document.id, 2),), 2, 7),
            LayoutActivity(first.id, (LayoutPage(document.id, 1),), 2, 7),
        ),
        (EvidenceKey(first.id, document.id, 1), EvidenceKey(second.id, document.id, 2)),
    )
    with world.uow_factory() as uow:
        uow.comprovante_layouts.create(saved, world.admin.id, 0)
        uow.commit()

    inputs = load(world)

    assert [a.activity_id for a in inputs.layout.activities] == [second.id, first.id]


def test_a_deleted_original_is_kept_in_the_documents_with_its_mark(official_chosen):
    world = official_chosen
    document = add_document(world)
    with world.uow_factory() as uow:
        uow.documents.mark_file_deleted(document.id, MOMENT)
        uow.commit()

    [found] = load(world).documents

    assert found.file_deleted_at is not None


def test_the_inputs_are_usable_after_the_read_and_no_transaction_stays_open(
    official_chosen, engine
):
    world = official_chosen
    activity = add_activity(world)
    document = add_document(world)
    link(world, activity, document, 1)

    inputs = load(world)

    with engine.connect() as conn:
        idle = conn.execute(
            text(
                "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database() "
                "AND pid <> pg_backend_pid() AND state = 'idle in transaction'"
            )
        ).scalar_one()
    assert idle == 0
    assert inputs.activities[0].id == activity.id
    assert inputs.documents[0].id == document.id
