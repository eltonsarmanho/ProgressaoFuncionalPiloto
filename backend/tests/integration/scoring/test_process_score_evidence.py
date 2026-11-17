"""VINC-04, VINC-06: the process score counts linked documents as evidence."""

import uuid
from datetime import date
from decimal import Decimal

from app.application.use_cases.scoring import ActivityData
from app.domain.entities.activity import ActivitySource, ActivityStatus
from app.domain.repositories.ports import ActivityEvidence
from app.domain.rules.scoring_alerts import NotScoredReason, ScoringAlertCode
from app.domain.rules.scoring_engine import RowStatus
from tests.integration.documents.factories import make_document

D = Decimal


def add(world, title, group=2, item=7, **kw):
    kw.setdefault("event_date", date(2023, 5, 10))
    kw.setdefault("quantity", D("1"))
    return world.create.execute(
        world.admin,
        world.process.id,
        ActivityData(title=title, group_number=group, item_number=item, **kw),
    )


def new_document(world):
    document = make_document(world.process, world.admin.id)
    with world.uow_factory() as uow:
        uow.documents.add(document)
        uow.commit()
    return document


def link(world, activity, document, page=1):
    evidence = ActivityEvidence(
        id=uuid.uuid4(),
        activity_id=activity.id,
        document_id=document.id,
        page_number=page,
        excerpt="trecho",
        created_by=world.admin.id,
    )
    with world.uow_factory() as uow:
        uow.evidences.add(evidence)
        uow.commit()
    return evidence


def score(world):
    return world.calc.execute(world.admin, world.process.id)


def row(result, activity):
    return next(r for r in result.rows if r.activity_id == activity.id)


def alerts(result, activity):
    return [a.code for a in row(result, activity).alerts]


def test_rows_show_the_link_count_and_the_counter_follows_the_links(official_chosen):
    world = official_chosen
    linked = add(world, "So vinculo")
    noted = add(world, "So nota", item=8, evidence_note="Certificado")
    neither = add(world, "Nada", item=9)
    link(world, linked, new_document(world))

    result = score(world).result

    assert result.counters.activities == 3
    assert result.counters.with_evidence == 2
    assert [row(result, a).evidence_count for a in (linked, noted, neither)] == [1, 0, 0]
    assert ScoringAlertCode.SEM_COMPROVANTE not in alerts(result, linked)
    assert ScoringAlertCode.SEM_COMPROVANTE not in alerts(result, noted)
    assert ScoringAlertCode.SEM_COMPROVANTE in alerts(result, neither)


def test_an_activity_with_several_documents_and_pages_counts_once_with_its_total(official_chosen):
    world = official_chosen
    activity = add(world, "Varios documentos")
    first, second = new_document(world), new_document(world)
    link(world, activity, first, page=1)
    link(world, activity, first, page=2)
    link(world, activity, second, page=1)

    result = score(world).result

    assert row(result, activity).evidence_count == 3
    assert result.counters.with_evidence == 1


def test_removing_the_last_link_brings_back_the_missing_proof_alert(official_chosen):
    world = official_chosen
    activity = add(world, "Vai perder o vinculo")
    evidence = link(world, activity, new_document(world))
    assert ScoringAlertCode.SEM_COMPROVANTE not in alerts(score(world).result, activity)

    with world.uow_factory() as uow:
        uow.evidences.remove(evidence.id)
        uow.commit()

    after = score(world).result
    assert ScoringAlertCode.SEM_COMPROVANTE in alerts(after, activity)
    assert (after.counters.with_evidence, row(after, activity).evidence_count) == (0, 0)


def test_links_change_neither_the_points_nor_the_total(official_chosen):
    world = official_chosen
    activity = add(world, "Mesmos pontos", quantity=D("4"), evidence_note="ok")
    before = score(world).result

    link(world, activity, new_document(world))
    after = score(world).result

    assert after.total == before.total == D("20")
    assert row(after, activity).points == row(before, activity).points


def test_suggested_draft_with_a_link_is_potential_and_counted_as_evidenced(official_chosen):
    world = official_chosen
    draft = world.create.execute(
        world.admin,
        world.process.id,
        ActivityData(
            title="Sugerida",
            group_number=2,
            item_number=7,
            quantity=D("2"),
            event_date=date(2023, 5, 10),
        ),
        source=ActivitySource.SUGERIDA_IA,
    )
    link(world, draft, new_document(world))

    result = score(world).result

    assert row(result, draft).status is RowStatus.POTENCIAL
    assert draft.status is ActivityStatus.AGUARDANDO_REVISAO
    assert result.counters.with_evidence == 1
    assert result.total == D("0")


def test_without_a_chosen_table_the_links_are_still_reported(world):
    activity = add(world, "Sem tabela")
    other = add(world, "Sem tabela nem vinculo", item=8)
    link(world, activity, new_document(world))

    result = score(world).result

    assert [row(result, a).reasons for a in (activity, other)] == [
        (NotScoredReason.SEM_TABELA,)
    ] * 2
    assert [row(result, a).evidence_count for a in (activity, other)] == [1, 0]
    assert result.counters.with_evidence == 1


def test_duplicates_linked_to_the_same_document_are_not_counted_twice(official_chosen):
    world = official_chosen
    first = add(world, "Banca de TCC", quantity=D("2"))
    second = add(world, "banca de tcc", quantity=D("2"))
    document = new_document(world)
    link(world, first, document)
    link(world, second, document)

    result = score(world).result

    statuses = sorted(row(result, a).status.value for a in (first, second))
    assert statuses == ["NAO_PONTUADA", "PONTUADA"]
    excluded = next(row(result, a) for a in (first, second) if row(result, a).reasons)
    assert excluded.reasons == (NotScoredReason.DUPLICIDADE,)
    assert result.total == D("10")
