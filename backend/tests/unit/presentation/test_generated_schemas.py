"""VER-03, VER-09, UIG-01 (T82): the schemas of the generated documents show states, versions,
alerts and files with size, carry no personal data nor file path, and refuse unknown fields."""

import json
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.application.use_cases.comprovante_layout import LayoutView
from app.application.use_cases.report_draft import ReportDraftView
from app.domain.entities.activity import Activity
from app.domain.entities.comprovante import (
    ComprovanteLayout,
    ComprovantePlan,
    LayoutActivity,
    LayoutPage,
    PageKind,
    PlanPage,
    Staleness,
)
from app.domain.entities.conclusion import ConclusionPreview, ConclusionResult
from app.domain.entities.generated import (
    DocumentFormat,
    DocumentKind,
    GeneratedDocument,
    GeneratedFile,
    GenerationAlert,
    GenerationAlertCode,
    GenerationCode,
    GenerationState,
)
from app.domain.entities.process import ProcessStatus
from app.domain.entities.report import DraftEntry, DraftSection, EntrySource, ReportDraft
from app.presentation.schemas.generated import (
    ConclusionIn,
    ConclusionOut,
    ConclusionPreviewOut,
    EntryTextIn,
    GeneratedDocumentDetailOut,
    GeneratedDocumentOut,
    GenerationRequest,
    LayoutActivityIn,
    LayoutPageIn,
    LayoutSaveIn,
    LayoutViewOut,
    MoveEntryIn,
    ReportDraftViewOut,
    SectionTextIn,
)

NOW = datetime(2026, 11, 18, 9, 0, tzinfo=UTC)
STORED_NAME = "a1b2c3d4e5f60718293a4b5c6d7e8f90.pdf"
SECRET_NOTE = "nota-sigilosa-do-docente"


def ready_row(**fields) -> GeneratedDocument:
    data = dict(
        id=uuid.uuid4(),
        process_id=uuid.uuid4(),
        kind=DocumentKind.TABELA,
        state=GenerationState.PRONTO,
        version_number=3,
        requested_by=uuid.uuid4(),
        requested_at=NOW,
        started_at=NOW,
        finished_at=NOW,
        snapshot={
            "table_version": {"id": None, "name": "Tabela oficial", "norm_reference": "Res. 1"},
            "interstice": {"start": "2022-11-23", "end": "2024-11-23"},
            "total": "211.00",
            "subtotals": {"2": "52.00", "3": "7.00"},
            "pit_total_hours": "92.00",
            "activities": [{"id": "a"}, {"id": "b"}],
            "excluded": {"pendentes": 1},
            "alerts": [],
        },
        alerts=(GenerationAlert(GenerationAlertCode.NUMERACAO_DIVERGENTE, "Numeração diferente."),),
        plan_hash="h" * 64,
        files=(
            GeneratedFile(DocumentFormat.DOCX, "x1.docx", "d" * 64, 1234),
            GeneratedFile(DocumentFormat.PDF, STORED_NAME, "e" * 64, 5678),
        ),
    )
    data.update(fields)
    return GeneratedDocument(**data)


def test_a_ready_row_shows_state_number_alerts_and_the_files_with_size():
    body = GeneratedDocumentOut.of(ready_row()).model_dump(mode="json")

    assert body["state"] == "PRONTO"
    assert body["version_number"] == 3
    assert body["alerts"] == [{"code": "NUMERACAO_DIVERGENTE", "message": "Numeração diferente."}]
    assert [(f["format"], f["size_bytes"], f["sha256"]) for f in body["files"]] == [
        ("DOCX", 1234, "d" * 64),
        ("PDF", 5678, "e" * 64),
    ]


def test_a_row_carries_no_stored_file_name_path_snapshot_or_requester():
    row = ready_row()
    text = json.dumps(GeneratedDocumentDetailOut.of(row).model_dump(mode="json"))

    for forbidden in (STORED_NAME, "x1.docx", "internal_name", "path", "plan_hash", "snapshot"):
        assert forbidden not in text
    assert str(row.requested_by) not in text


def test_a_failed_row_shows_the_code_and_the_message_and_no_number():
    row = ready_row(
        state=GenerationState.FALHOU,
        version_number=None,
        files=(),
        snapshot=None,
        alerts=(),
        error_code=GenerationCode.INTERROMPIDA,
        error_message="O servidor reiniciou durante a geração.",
    )

    body = GeneratedDocumentDetailOut.of(row).model_dump(mode="json")

    assert (body["state"], body["version_number"], body["files"]) == ("FALHOU", None, [])
    assert body["error_code"] == "INTERROMPIDA"
    assert body["error_message"] == "O servidor reiniciou durante a geração."
    assert body["summary"] is None


def test_the_detail_summarizes_the_snapshot_with_the_totals_the_document_showed():
    summary = GeneratedDocumentDetailOut.of(ready_row()).summary

    assert summary.table_name == "Tabela oficial"
    assert (summary.interstice_start, summary.interstice_end) == (
        date(2022, 11, 23),
        date(2024, 11, 23),
    )
    assert (summary.total, summary.pit_total_hours) == ("211.00", "92.00")
    assert summary.subtotals == {"2": "52.00", "3": "7.00"}
    assert (summary.activity_count, summary.excluded) == (2, {"pendentes": 1})


@pytest.mark.parametrize(
    ("schema", "body"),
    [
        (GenerationRequest, {"kind": "TABELA"}),
        (EntryTextIn, {"expected_version": 1, "text": "t"}),
        (SectionTextIn, {"expected_version": 1, "free_text": "t"}),
        (MoveEntryIn, {"expected_version": 1, "section_key": "1.1"}),
        (LayoutSaveIn, {"expected_version": 0, "activities": []}),
        (ConclusionIn, {"expected_version": 1, "confirmar": True}),
    ],
)
def test_a_body_is_accepted_as_documented_and_refuses_a_field_it_does_not_know(schema, body):
    assert schema(**body)
    with pytest.raises(ValidationError) as refused:
        schema(**body, extra_field="x")
    assert refused.value.errors()[0]["type"] == "extra_forbidden"


def test_the_kind_of_a_request_must_be_one_of_the_three_documents():
    with pytest.raises(ValidationError):
        GenerationRequest(kind="PARECER")


def test_a_layout_body_becomes_the_domain_arrangement_and_refuses_page_zero():
    activity_id, document_id = uuid.uuid4(), uuid.uuid4()
    body = LayoutSaveIn(
        expected_version=2,
        activities=[
            {
                "activity_id": activity_id,
                "group_number": 2,
                "item_number": 7,
                "pages": [{"document_id": document_id, "page": 3, "repeat_justification": "dois"}],
            }
        ],
    )

    entry = body.activities[0].to_domain()

    assert entry == LayoutActivity(
        activity_id, (LayoutPage(document_id, 3, "dois"),), group_number=2, item_number=7
    )
    with pytest.raises(ValidationError):
        LayoutPageIn(document_id=document_id, page=0)
    with pytest.raises(ValidationError):
        LayoutActivityIn(activity_id=activity_id, pages=[{"document_id": document_id, "page": 0}])


def test_the_draft_view_names_activities_without_their_notes_and_lists_the_item_names():
    activity = Activity(
        id=uuid.uuid4(),
        process_id=uuid.uuid4(),
        title="Orientação de TCC",
        created_by=uuid.uuid4(),
        group_number=2,
        item_number=7,
        description="descrição longa",
        event_date=date(2023, 5, 10),
        evidence_note=SECRET_NOTE,
        quantity=Decimal("1"),
    )
    draft = ReportDraft(
        process_id=activity.process_id,
        template_id="ufpa",
        template_version=1,
        version=0,
        sections=(
            DraftSection(
                "1.1",
                "Ensino",
                "livre",
                (DraftEntry(activity.id, "Texto da atividade.", EntrySource.MODELO),),
            ),
        ),
    )
    view = ReportDraftView(
        draft=draft,
        saved=False,
        empty_sections=("1.2",),
        alerts=(),
        activities=(activity,),
        item_names={(2, 7): "Orientação concluída", (2, 1): "Outro"},
    )

    body = ReportDraftViewOut.of_view(view).model_dump(mode="json")

    assert body["version"] == 0 and body["saved"] is False
    assert body["empty_sections"] == ["1.2"]
    assert body["sections"][0]["entries"][0] == {
        "activity_id": str(activity.id),
        "text": "Texto da atividade.",
        "source": "MODELO",
        "warnings": [],
    }
    assert body["activities"] == [
        {
            "id": str(activity.id),
            "title": "Orientação de TCC",
            "group_number": 2,
            "item_number": 7,
            "event_date": "2023-05-10",
            "academic_period": None,
        }
    ]
    assert body["item_names"] == [
        {"group_number": 2, "item_number": 1, "name": "Outro"},
        {"group_number": 2, "item_number": 7, "name": "Orientação concluída"},
    ]
    assert SECRET_NOTE not in json.dumps(body)


def test_the_layout_view_carries_the_saved_flag_the_staleness_and_the_numbering():
    activity_id, document_id = uuid.uuid4(), uuid.uuid4()
    plan = ComprovantePlan(
        pages=(
            PlanPage(PageKind.CAPA, 1),
            PlanPage(PageKind.SUMARIO, 2),
            PlanPage(PageKind.ORIGINAL, 3, 2, document_id, 5),
        ),
        plan_hash="p" * 64,
    )
    view = LayoutView(
        layout=ComprovanteLayout(
            uuid.uuid4(), (LayoutActivity(activity_id, (LayoutPage(document_id, 5),), 2, 7),), (), 4
        ),
        saved=True,
        staleness=Staleness(joined_activity_ids=(activity_id,)),
        invalid=(),
        plan=plan,
        alerts=(GenerationAlert(GenerationAlertCode.ARRANJO_DESATUALIZADO, "Desatualizado."),),
    )

    body = LayoutViewOut.of(view).model_dump(mode="json")

    assert body["saved"] is True and body["stale"] is True
    assert body["layout"]["version"] == 4
    assert body["staleness"]["joined_activity_ids"] == [str(activity_id)]
    assert [(p["kind"], p["number"], p["source_page"]) for p in body["plan"]["pages"]] == [
        ("CAPA", 1, None),
        ("SUMARIO", 2, None),
        ("ORIGINAL", 3, 5),
    ]
    assert body["alerts"] == [{"code": "ARRANJO_DESATUALIZADO", "message": "Desatualizado."}]


def test_the_conclusion_preview_gives_the_state_of_each_kind():
    preview = ConclusionPreview(
        files=3,
        bytes=4096,
        artifacts={DocumentKind.TABELA: True, DocumentKind.RELATORIO: False},
    )

    body = ConclusionPreviewOut.of(preview).model_dump(mode="json")

    assert body == {
        "files": 3,
        "bytes": 4096,
        "artifacts": {"TABELA": True, "RELATORIO": False},
    }


def test_the_conclusion_result_uses_the_documented_names_and_the_partial_alert():
    result = ConclusionResult(
        ProcessStatus.EM_ANDAMENTO,
        files_removed=2,
        files_pending=1,
        bytes_freed=900,
        alerts=(GenerationAlert(GenerationAlertCode.EXCLUSAO_PARCIAL, "Falta 1 arquivo."),),
    )

    body = ConclusionOut.of(result).model_dump(mode="json")

    assert body == {
        "status": "EM_ANDAMENTO",
        "arquivos_removidos": 2,
        "arquivos_pendentes": 1,
        "bytes_liberados": 900,
        "alertas": [{"code": "EXCLUSAO_PARCIAL", "message": "Falta 1 arquivo."}],
    }
