"""DEL-03, DEL-08: preview, result and check of the conclusion."""

import dataclasses

import pytest

from app.domain.entities.conclusion import ConclusionCheck, ConclusionPreview, ConclusionResult
from app.domain.entities.generated import (
    DocumentKind,
    GenerationAlert,
    GenerationAlertCode,
    GenerationCode,
)
from app.domain.entities.process import ProcessStatus


def test_the_preview_keeps_files_bytes_and_a_flag_per_kind_of_artifact():
    artifacts = {
        DocumentKind.TABELA: True,
        DocumentKind.RELATORIO: False,
        DocumentKind.COMPROVANTE: True,
    }

    preview = ConclusionPreview(files=3, bytes=1_500_000, artifacts=artifacts)

    assert (preview.files, preview.bytes) == (3, 1_500_000)
    assert preview.artifacts[DocumentKind.TABELA] is True
    assert preview.artifacts[DocumentKind.RELATORIO] is False
    assert preview.artifacts[DocumentKind.COMPROVANTE] is True


def test_the_result_keeps_status_counts_bytes_and_alerts():
    alert = GenerationAlert(GenerationAlertCode.EXCLUSAO_PARCIAL, "1 arquivo pendente")

    result = ConclusionResult(
        status=ProcessStatus.EM_ANDAMENTO,
        files_removed=2,
        files_pending=1,
        bytes_freed=4096,
        alerts=(alert,),
    )

    assert result.status is ProcessStatus.EM_ANDAMENTO
    assert (result.files_removed, result.files_pending, result.bytes_freed) == (2, 1, 4096)
    assert result.alerts == (alert,)


def test_a_result_without_alerts_has_an_empty_tuple():
    result = ConclusionResult(ProcessStatus.CONCLUIDO, 3, 0, 100)

    assert result.alerts == ()


def test_a_check_that_passes_has_no_code_and_no_missing_kinds():
    check = ConclusionCheck()

    assert (check.code, check.missing_kinds, check.allowed) == (None, (), True)


def test_a_check_that_refuses_carries_the_code_and_the_missing_kinds():
    check = ConclusionCheck(
        GenerationCode.ARTEFATOS_PENDENTES, (DocumentKind.TABELA, DocumentKind.COMPROVANTE)
    )

    assert check.allowed is False
    assert check.code is GenerationCode.ARTEFATOS_PENDENTES
    assert check.missing_kinds == (DocumentKind.TABELA, DocumentKind.COMPROVANTE)


def test_the_conclusion_records_are_immutable():
    result = ConclusionResult(ProcessStatus.CONCLUIDO, 0, 0, 0)

    with pytest.raises(dataclasses.FrozenInstanceError):
        result.files_removed = 1  # type: ignore[misc]
