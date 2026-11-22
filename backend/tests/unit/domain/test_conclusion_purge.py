"""DEL-03, DEL-08, DEL-09, DEL-13: preview and result of removing the input documents."""

from dataclasses import dataclass
from datetime import UTC, datetime

from app.domain.entities.conclusion import ConclusionPreview
from app.domain.entities.generated import ARTIFACT_KINDS, DocumentKind, GenerationAlertCode
from app.domain.entities.process import ProcessStatus
from app.domain.rules.conclusion_rules import purge_outcome, summarize_purge

DELETED_AT = datetime(2026, 11, 18, 12, 0, tzinfo=UTC)


@dataclass
class FakeDocument:
    size_bytes: int
    file_deleted_at: datetime | None = None


def test_the_preview_counts_only_documents_that_still_have_a_file_and_sums_their_bytes():
    documents = [
        FakeDocument(1_000),
        FakeDocument(2_500_000, file_deleted_at=DELETED_AT),
        FakeDocument(250),
    ]

    preview = summarize_purge(documents)

    assert (preview.files, preview.bytes) == (2, 1_250)


def test_a_process_without_documents_has_zero_files_and_zero_bytes():
    preview = summarize_purge([])

    assert (preview.files, preview.bytes) == (0, 0)


def test_a_process_whose_files_are_all_deleted_has_zero_files_and_zero_bytes():
    preview = summarize_purge([FakeDocument(10, DELETED_AT), FakeDocument(20, DELETED_AT)])

    assert (preview.files, preview.bytes) == (0, 0)


def test_the_preview_says_which_kinds_have_a_ready_version():
    preview = summarize_purge([], ready_kinds={DocumentKind.TABELA, DocumentKind.COMPROVANTE})

    assert preview.artifacts == {
        DocumentKind.TABELA: True,
        DocumentKind.RELATORIO: False,
        DocumentKind.COMPROVANTE: True,
    }


def test_without_ready_kinds_every_kind_is_marked_missing():
    preview = summarize_purge([FakeDocument(5)])

    assert preview.artifacts == dict.fromkeys(ARTIFACT_KINDS, False)
    assert isinstance(preview, ConclusionPreview)


def test_an_outcome_without_pending_files_concludes_the_process():
    result = purge_outcome(removed=3, failed=0, bytes_freed=4_096)

    assert result.status is ProcessStatus.CONCLUIDO
    assert (result.files_removed, result.files_pending, result.bytes_freed) == (3, 0, 4_096)
    assert result.alerts == ()


def test_an_outcome_with_one_pending_file_keeps_the_process_in_progress_with_the_alert():
    result = purge_outcome(removed=2, failed=1, bytes_freed=900)

    assert result.status is ProcessStatus.EM_ANDAMENTO
    assert (result.files_removed, result.files_pending, result.bytes_freed) == (2, 1, 900)
    assert [alert.code for alert in result.alerts] == [GenerationAlertCode.EXCLUSAO_PARCIAL]


def test_the_partial_alert_message_carries_the_counts_and_no_file_name():
    (alert,) = purge_outcome(removed=2, failed=1, bytes_freed=900).alerts

    assert alert.message == "2 arquivo(s) removido(s) e 1 pendente(s); repita a conclusão."


def test_repeating_the_outcome_of_a_concluded_process_gives_zeros_and_the_same_status():
    first = purge_outcome(removed=3, failed=0, bytes_freed=4_096)
    repeated = purge_outcome(removed=0, failed=0, bytes_freed=0)

    assert repeated.status is first.status is ProcessStatus.CONCLUIDO
    assert (repeated.files_removed, repeated.files_pending, repeated.bytes_freed) == (0, 0, 0)
    assert repeated.alerts == ()


def test_an_outcome_where_nothing_was_removed_but_all_failed_stays_in_progress():
    result = purge_outcome(removed=0, failed=4, bytes_freed=0)

    assert result.status is ProcessStatus.EM_ANDAMENTO
    assert result.files_pending == 4
    assert result.alerts[0].code is GenerationAlertCode.EXCLUSAO_PARCIAL
