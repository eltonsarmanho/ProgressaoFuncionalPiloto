"""FORA-01, FORA-03, FORA-05, FORA-07, FORA-09: ProcessDocument with a document outside the
interstice, and what the reprocessing does to the activities that were already linked to it."""

import dataclasses
from datetime import date

from app.application.services.generation_inputs import load_generation_inputs
from app.application.use_cases.scoring import ActivityData
from app.domain.entities.activity import ActivityStatus
from app.domain.entities.audit import AuditAction
from app.domain.entities.document import DocAlertCode, DocumentStatus, RunStatus
from app.domain.rules.activity_validity import InvalidReason
from tests.integration.doc_usecases.support import link
from tests.integration.doc_usecases.test_process_document import (
    banca_payload,
    banca_text,
    process_banca,
    state,
)
from tests.unit.application.analyzer_fakes import FakeAi, FakeTextExtractor, text_page

OUTSIDE = DocAlertCode.DOCUMENTO_FORA_DO_INTERSTICIO.value
# the banca of banca_text is dated 12/03/2023
AROUND_THE_BANCA = (date(2022, 11, 23), date(2024, 11, 23))
AFTER_THE_BANCA = (date(2024, 1, 1), date(2025, 12, 31))


def set_interstice(docs, interval):
    with docs.world.uow_factory() as uow:
        current = uow.processes.get(docs.world.process.id)
        changed = dataclasses.replace(current, start_date=interval[0], end_date=interval[1])
        uow.processes.update(changed, current.version)
        uow.commit()


def reprocess(docs, document):
    w = docs.world
    docs.clock.advance(minutes=5)
    docs.reprocess.execute(w.docente, document.id)
    extractor = FakeTextExtractor(text_page(1, banca_text(w)))
    docs.run_next_job(docs.processor(extractor, FakeAi(banca_payload(w))))


def test_a_document_outside_the_interstice_is_processed_with_no_activity_and_no_review(docs):
    set_interstice(docs, AFTER_THE_BANCA)

    document = process_banca(docs, "fora")

    found = state(docs, document)
    assert found.document.status is DocumentStatus.PROCESSADO
    assert found.document.status_code == OUTSIDE
    assert found.document.suggested_category is None
    assert found.activities == []
    assert found.evidences == []
    [run] = found.runs
    [alert] = [a for a in run.warnings if a["code"] == OUTSIDE]
    assert alert["detail"] == {
        "document_date": "2023-03-12",
        "date_precision": "DAY",
        "interstice_start": "2024-01-01",
        "interstice_end": "2025-12-31",
    }


def test_a_document_inside_the_interstice_has_no_alert_and_creates_the_activity(docs):
    document = process_banca(docs, "dentro")

    found = state(docs, document)

    assert found.document.status_code is None
    assert [a.title for a in found.activities] == ["Estudo Ficticio sobre Dados Abertos"]
    assert all(w["code"] != OUTSIDE for w in found.runs[0].warnings)


def test_reprocessing_after_widening_the_interstice_drops_the_alert_and_creates_the_activity(docs):
    set_interstice(docs, AFTER_THE_BANCA)
    document = process_banca(docs, "ampliar")
    set_interstice(docs, AROUND_THE_BANCA)

    reprocess(docs, document)

    found = state(docs, document)
    assert found.document.status is DocumentStatus.PROCESSADO
    assert found.document.status_code is None
    assert found.document.suggested_category == "BANCA_TCC_GRADUACAO"
    [created] = found.activities
    assert created.status is ActivityStatus.AGUARDANDO_REVISAO
    active = [r for r in found.runs if r.status is RunStatus.ATIVA]
    assert all(w["code"] != OUTSIDE for run in active for w in run.warnings)


def test_reprocessing_after_narrowing_the_interstice_replaces_the_old_draft_and_flags_it(docs):
    document = process_banca(docs, "restringir")
    set_interstice(docs, AFTER_THE_BANCA)

    reprocess(docs, document)

    found = state(docs, document)
    assert found.document.status_code == OUTSIDE
    assert found.document.status is DocumentStatus.PROCESSADO
    assert [a.status for a in found.activities] == [ActivityStatus.REJEITADA]
    assert found.evidences[0].run_id == found.runs[0].id  # the old draft only


# --- FORA-03 (AD-018): the work already done on the activities of a document that became outside


def validate(w, activity):
    return w.change_status.execute(
        w.docente, activity.id, ActivityStatus.VALIDADA, activity.version, None
    )


def activity_of(docs, document):
    """The one activity the document's runs created."""
    found = state(docs, document)
    runs = {r.id for r in found.runs}
    [created] = [a for a in found.activities if a.extraction_run_id in runs]
    return created


def stored(docs, activity_id):
    with docs.world.uow_factory() as uow:
        return uow.activities.get(activity_id)


def audit_of(docs, entity, entity_id):
    with docs.world.uow_factory() as uow:
        return list(uow.audit.list_for(entity, str(entity_id)))


def active_count(docs, document):
    """What the Etapa 2 list shows as the activities of the document (the ones not rejected)."""
    with docs.world.uow_factory() as uow:
        return uow.evidences.counts_for_documents([document.id])[document.id]


def test_a_validated_activity_linked_only_to_the_document_is_rejected_with_the_audit_reason(docs):
    w = docs.world
    document = process_banca(docs, "validada")
    draft = activity_of(docs, document)
    validate(w, draft)
    set_interstice(docs, AFTER_THE_BANCA)

    reprocess(docs, document)

    assert stored(docs, draft.id).status is ActivityStatus.REJEITADA
    assert state(docs, document).document.status_code == OUTSIDE
    assert active_count(docs, document) == 0
    rejection = audit_of(docs, "activity", draft.id)[-1]
    assert rejection.action is AuditAction.STATUS
    assert rejection.changes == {"status": {"before": "VALIDADA", "after": "REJEITADA"}}
    assert rejection.justification == OUTSIDE
    assert rejection.user_id is None


def test_an_edited_activity_linked_only_to_the_document_is_rejected_too(docs):
    w = docs.world
    document = process_banca(docs, "editada")
    draft = activity_of(docs, document)
    edited = w.update.execute(
        w.docente,
        draft.id,
        ActivityData(title="Editada pelo usuario", group_number=3, item_number=4),
        draft.version,
        None,
    )
    assert edited.status is ActivityStatus.AGUARDANDO_REVISAO and edited.version > 1
    set_interstice(docs, AFTER_THE_BANCA)

    reprocess(docs, document)

    assert stored(docs, draft.id).status is ActivityStatus.REJEITADA
    assert audit_of(docs, "activity", draft.id)[-1].justification == OUTSIDE


def test_the_activities_of_other_documents_and_the_manual_ones_are_left_alone(docs):
    w = docs.world
    document = process_banca(docs, "alvo")
    neighbour_document = process_banca(docs, "vizinho")
    target = activity_of(docs, document)
    neighbour = activity_of(docs, neighbour_document)
    validate(w, neighbour)
    manual = w.create.execute(w.docente, w.process.id, ActivityData(title="Manual"))
    set_interstice(docs, AFTER_THE_BANCA)

    reprocess(docs, document)

    assert stored(docs, target.id).status is ActivityStatus.REJEITADA
    assert stored(docs, neighbour.id).status is ActivityStatus.VALIDADA
    assert stored(docs, manual.id).status is ActivityStatus.VALIDADA
    assert all(e.justification != OUTSIDE for e in audit_of(docs, "activity", neighbour.id))
    assert state(docs, neighbour_document).document.status_code is None


def test_an_activity_with_evidence_from_another_document_stays_without_the_outside_evidence(docs):
    w = docs.world
    document = process_banca(docs, "fora-depois")
    other = process_banca(docs, "continua")
    shared = activity_of(docs, document)
    validate(w, shared)
    kept = link(w, shared, other, page=1, excerpt="outro trecho")
    [outside_evidence] = state(docs, document).evidences
    set_interstice(docs, AFTER_THE_BANCA)

    reprocess(docs, document)

    assert stored(docs, shared.id).status is ActivityStatus.VALIDADA
    assert state(docs, document).evidences == []
    with w.uow_factory() as uow:
        assert [e.id for e in uow.evidences.list_for_activity(shared.id)] == [kept.id]
    unlink = audit_of(docs, "activity_evidence", outside_evidence.id)[-1]
    assert unlink.action is AuditAction.UPDATE
    assert unlink.justification == OUTSIDE


def test_reprocessing_again_with_a_wider_interstice_creates_the_activity_and_keeps_the_rejected(
    docs,
):
    w = docs.world
    document = process_banca(docs, "ampliada")
    first = activity_of(docs, document)
    validate(w, first)
    set_interstice(docs, AFTER_THE_BANCA)
    reprocess(docs, document)
    set_interstice(docs, AROUND_THE_BANCA)

    reprocess(docs, document)

    found = state(docs, document)
    assert found.document.status_code is None
    assert stored(docs, first.id).status is ActivityStatus.REJEITADA
    [fresh] = [a for a in found.activities if a.id != first.id]
    assert fresh.status is ActivityStatus.AGUARDANDO_REVISAO
    assert len(found.activities) == 2
    assert active_count(docs, document) == 1


def test_the_score_does_not_count_the_rejected_activity(official_chosen, docs):
    w = official_chosen
    document = process_banca(docs, "pontuada")
    draft = activity_of(docs, document)
    # EDT-02: the date has to be inside the interstice when it is edited, so the interstice that
    # the process gets later is set first and the user moves the date into it
    set_interstice(docs, AFTER_THE_BANCA)
    edited = w.update.execute(
        w.docente,
        draft.id,
        ActivityData(
            title=draft.title, group_number=3, item_number=4, event_date=date(2025, 5, 5)
        ),
        draft.version,
        None,
    )
    validate(w, edited)
    before = w.calc.execute(w.docente, w.process.id)
    assert before.result.total > 0

    reprocess(docs, document)

    after = w.calc.execute(w.docente, w.process.id)
    # SEG-01: the rejected activity is not valid and has no row
    assert after.result.rows == ()
    assert after.result.total == 0
    assert after.result.validity[draft.id].reason is InvalidReason.REJEITADA


def test_the_generated_documents_do_not_read_the_rejected_activity_or_its_evidence(
    official_chosen, docs
):
    w = official_chosen
    document = process_banca(docs, "gerados")
    draft = activity_of(docs, document)
    validate(w, draft)
    set_interstice(docs, AFTER_THE_BANCA)

    reprocess(docs, document)

    with w.uow_factory() as uow:
        inputs = load_generation_inputs(uow, uow.processes.get(w.process.id))
    assert inputs.activities == ()
    assert inputs.evidences == ()
    assert inputs.excluded == {}  # SEG-01: the rejected activity is not valid, not left out
