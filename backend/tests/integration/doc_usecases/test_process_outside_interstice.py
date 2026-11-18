"""FORA-01, FORA-05, FORA-07, FORA-09: ProcessDocument with a document outside the interstice."""

import dataclasses
from datetime import date

from app.domain.entities.activity import ActivityStatus
from app.domain.entities.document import DocAlertCode, DocumentStatus, RunStatus
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
