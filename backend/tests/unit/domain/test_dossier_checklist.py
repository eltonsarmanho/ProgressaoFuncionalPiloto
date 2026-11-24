"""DOS-01, DOS-02, DOS-03, DOS-05, DOS-06: the state of each item of the dossier checklist."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.domain.entities.board import BoardOrdinance
from app.domain.entities.generated import DocumentKind, GeneratedDocument, GenerationState
from app.domain.rules.dossier_checklist import ChecklistState, dossier_checklist, latest_ready
from app.infrastructure.documents.config_loader import load_dossier_order
from tests.unit.domain.board_document_support import MEMBERS, member, ordinance

ORDER = load_dossier_order()
NOW = datetime(2026, 11, 22, 12, 0, tzinfo=UTC)
TABLE_V1 = uuid4()
TABLE_V2 = uuid4()


def document(
    kind, number, state=GenerationState.PRONTO, table_version: UUID | None = None
) -> GeneratedDocument:
    snapshot = None if table_version is None else {"table_version": {"id": str(table_version)}}
    return GeneratedDocument(
        id=uuid4(),
        process_id=uuid4(),
        kind=kind,
        state=state,
        version_number=number if state is GenerationState.PRONTO else None,
        requested_by=uuid4(),
        requested_at=NOW,
        snapshot=snapshot,
    )


def checklist(ready=None, board: BoardOrdinance | None = None, delivered=(), current=None):
    return dossier_checklist(ORDER, ready or {}, board, set(delivered), current)


def by_key(items):
    return {item.key: item for item in items}


# --- order (DOS-01) -------------------------------------------------------------------------


def test_the_list_follows_the_order_of_the_file_with_its_nine_items():
    items = checklist()

    assert [i.key for i in items] == [i.key for i in ORDER]
    assert [i.order for i in items] == [1, 2, 3, 4, 5, 6, 7, 8, 9]
    assert [i.title for i in items] == [i.title for i in ORDER]
    assert len(items) == 9


# --- the independent test of the spec: three generated, six pending (DOS-02, DOS-05) --------


def test_only_the_table_the_report_and_the_proof_ready_give_three_generated_and_six_pending():
    table, report, proof = (
        document(DocumentKind.TABELA, 4),
        document(DocumentKind.RELATORIO, 2),
        document(DocumentKind.COMPROVANTE, 7),
    )
    ready = {DocumentKind.TABELA: table, DocumentKind.RELATORIO: report}
    ready[DocumentKind.COMPROVANTE] = proof

    items = by_key(checklist(ready))

    generated = [i for i in items.values() if i.state is ChecklistState.GERADO]
    pending = [i for i in items.values() if i.state is ChecklistState.PENDENTE]
    assert {i.key for i in generated} == {"TABELA", "RELATORIO", "COMPROVANTE"}
    assert len(pending) == 6
    assert (items["TABELA"].version_number, items["TABELA"].generation_id) == (4, table.id)
    assert (items["RELATORIO"].version_number, items["RELATORIO"].generation_id) == (2, report.id)
    assert (items["COMPROVANTE"].version_number, items["COMPROVANTE"].generation_id) == (
        7,
        proof.id,
    )
    assert items["REQUERIMENTO"].version_number is None
    assert items["REQUERIMENTO"].generation_id is None


def test_the_requerimento_and_the_parecer_are_generated_when_they_have_a_ready_version():
    request, opinion = document(DocumentKind.REQUERIMENTO, 1), document(DocumentKind.PARECER, 3)

    items = by_key(checklist({DocumentKind.REQUERIMENTO: request, DocumentKind.PARECER: opinion}))

    assert items["REQUERIMENTO"].state is ChecklistState.GERADO
    assert items["PARECER"].state is ChecklistState.GERADO
    assert (items["PARECER"].version_number, items["PARECER"].generation_id) == (3, opinion.id)


def test_the_last_ready_version_counts_and_a_newer_failure_does_not_hide_it():
    rows = [
        document(DocumentKind.TABELA, 1),
        document(DocumentKind.TABELA, 2),
        document(DocumentKind.TABELA, None, GenerationState.FALHOU),
        document(DocumentKind.TABELA, None, GenerationState.GERANDO),
        document(DocumentKind.RELATORIO, None, GenerationState.FALHOU),
    ]

    ready = latest_ready(rows)
    items = by_key(checklist(ready))

    assert set(ready) == {DocumentKind.TABELA}
    assert items["TABELA"].state is ChecklistState.GERADO
    assert items["TABELA"].version_number == 2
    assert items["TABELA"].generation_id == rows[1].id
    assert items["RELATORIO"].state is ChecklistState.PENDENTE


# --- board ordinance (DOS-03) ---------------------------------------------------------------


def test_an_ordinance_without_members_is_pending():
    items = by_key(checklist(board=ordinance(members=[])))

    assert items["PORTARIA_BANCA"].state is ChecklistState.PENDENTE


def test_an_ordinance_with_one_member_is_registered():
    items = by_key(checklist(board=ordinance(members=[member("Só Um Membro")])))

    assert items["PORTARIA_BANCA"].state is ChecklistState.REGISTRADA


def test_no_ordinance_at_all_is_pending_and_a_full_one_is_registered():
    assert by_key(checklist())["PORTARIA_BANCA"].state is ChecklistState.PENDENTE
    assert by_key(checklist(board=ordinance(MEMBERS)))["PORTARIA_BANCA"].state is (
        ChecklistState.REGISTRADA
    )


# --- manual items (DOS-04 state, DOS-05) ----------------------------------------------------


def test_a_manual_item_marked_is_delivered_and_unmarked_is_pending():
    items = by_key(checklist(delivered=["CURRICULO_LATTES"]))

    assert items["CURRICULO_LATTES"].state is ChecklistState.ENTREGUE
    assert items["PORTARIA_ULTIMA_PROGRESSAO"].state is ChecklistState.PENDENTE
    assert items["DECLARACAO_EXERCICIOS_ANTERIORES"].state is ChecklistState.PENDENTE


def test_a_mark_on_a_key_that_is_not_manual_is_ignored():
    items = by_key(checklist(delivered=["TABELA", "PORTARIA_BANCA", "PARECER", "REQUERIMENTO"]))

    assert items["TABELA"].state is ChecklistState.PENDENTE
    assert items["PORTARIA_BANCA"].state is ChecklistState.PENDENTE
    assert items["PARECER"].state is ChecklistState.PENDENTE
    assert items["REQUERIMENTO"].state is ChecklistState.PENDENTE


def test_an_item_without_version_registration_or_mark_is_pending():
    assert {i.state for i in checklist()} == {ChecklistState.PENDENTE}


def test_a_mark_does_not_replace_a_ready_version_of_a_generated_item():
    ready = {DocumentKind.TABELA: document(DocumentKind.TABELA, 1)}

    items = by_key(checklist(ready, delivered=["TABELA"]))

    assert items["TABELA"].state is ChecklistState.GERADO


# --- table made with another version of the scoring table (DOS-06) --------------------------


def test_the_table_made_with_another_scoring_table_version_is_marked_outdated():
    ready = {DocumentKind.TABELA: document(DocumentKind.TABELA, 2, table_version=TABLE_V1)}

    items = by_key(checklist(ready, current=TABLE_V2))

    assert items["TABELA"].outdated_table is True


def test_the_table_made_with_the_current_scoring_table_version_is_not_outdated():
    ready = {DocumentKind.TABELA: document(DocumentKind.TABELA, 2, table_version=TABLE_V2)}

    assert by_key(checklist(ready, current=TABLE_V2))["TABELA"].outdated_table is False


def test_without_both_versions_the_table_is_not_marked_outdated():
    old = {DocumentKind.TABELA: document(DocumentKind.TABELA, 2)}  # snapshot without version id
    new = {DocumentKind.TABELA: document(DocumentKind.TABELA, 2, table_version=TABLE_V1)}

    assert by_key(checklist(old, current=TABLE_V2))["TABELA"].outdated_table is False
    assert by_key(checklist(new, current=None))["TABELA"].outdated_table is False
    assert by_key(checklist())["TABELA"].outdated_table is False


def test_only_the_table_item_can_be_outdated():
    ready = {
        kind: document(kind, 1, table_version=TABLE_V1)
        for kind in (DocumentKind.TABELA, DocumentKind.RELATORIO, DocumentKind.COMPROVANTE)
    }

    items = by_key(checklist(ready, current=TABLE_V2))

    assert [k for k, i in items.items() if i.outdated_table] == ["TABELA"]
