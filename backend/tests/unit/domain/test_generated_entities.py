"""VER-01, VER-04, VER-05, REL-13: generated document entities, states and codes."""

import dataclasses
from datetime import UTC, datetime
from itertools import product
from uuid import uuid4

import pytest

from app.domain.entities.generated import (
    DocumentFormat,
    DocumentKind,
    GeneratedDocument,
    GeneratedFile,
    GenerationAlert,
    GenerationAlertCode,
    GenerationCode,
    GenerationState,
    WordingJob,
    can_transition,
)

NOW = datetime(2026, 11, 18, 9, 0, tzinfo=UTC)

REFUSAL_CODES = {
    "SEM_ATIVIDADES_VALIDADAS", "TABELA_NAO_ESCOLHIDA", "ATIVIDADE_SEM_DESCRICAO",
    "ATIVIDADE_SEM_CATEGORIA",
    "COMPROVANTE_GRANDE_DEMAIS", "IMAGEM_GRANDE_DEMAIS", "ORIGINAL_INDISPONIVEL",
    "ORIGINAIS_EXCLUIDOS", "INTERROMPIDA", "ESPACO_INSUFICIENTE", "ERRO_INTERNO",
    "GERACAO_EM_ANDAMENTO", "REDACAO_EM_ANDAMENTO", "ARTEFATOS_PENDENTES",
    "CONFIRMACAO_OBRIGATORIA", "OPERACAO_EM_ANDAMENTO", "CONCLUSAO_EXIGE_EXCLUSAO",
    "ARQUIVO_EXCLUIDO", "PAGINA_FORA_DO_DOCUMENTO", "VERSAO_DESATUALIZADA",
    "PROCESSO_SOMENTE_LEITURA",
}  # fmt: skip
ALERT_CODES = {
    "ATIVIDADE_SEM_COMPROVANTE", "REDACAO_REJEITADA", "REDACAO_INDISPONIVEL",
    "ARRANJO_DESATUALIZADO", "NUMERACAO_DIVERGENTE", "ATIVIDADES_FORA_DO_DOCUMENTO",
    "PAGINA_REPETIDA_JUSTIFICADA", "PAGINA_RASTERIZADA", "RASCUNHO_DESATUALIZADO",
    "EXCLUSAO_PARCIAL",
}  # fmt: skip

ALLOWED = {
    (GenerationState.GERANDO, GenerationState.PRONTO),
    (GenerationState.GERANDO, GenerationState.FALHOU),
}


@pytest.mark.parametrize(("current", "target"), list(product(GenerationState, GenerationState)))
def test_only_gerando_to_pronto_or_falhou_is_a_valid_transition(current, target):
    assert can_transition(current, target) is ((current, target) in ALLOWED)


def test_the_three_kinds_the_two_formats_and_the_three_states_exist():
    assert [k.value for k in DocumentKind] == ["TABELA", "RELATORIO", "COMPROVANTE"]
    assert [f.value for f in DocumentFormat] == ["DOCX", "PDF"]
    assert [s.value for s in GenerationState] == ["GERANDO", "PRONTO", "FALHOU"]


def test_the_refusal_codes_have_the_exact_names_of_the_design():
    assert {c.value for c in GenerationCode} == REFUSAL_CODES
    assert all(c.name == c.value for c in GenerationCode)


def test_the_alert_codes_have_the_exact_names_of_the_design():
    assert {c.value for c in GenerationAlertCode} == ALERT_CODES
    assert all(c.name == c.value for c in GenerationAlertCode)


def test_a_generated_document_keeps_its_fields_and_its_files():
    process_id, user_id = uuid4(), uuid4()
    pdf = GeneratedFile(DocumentFormat.PDF, "abc.pdf", "f" * 64, 1234)
    alert = GenerationAlert(GenerationAlertCode.ATIVIDADE_SEM_COMPROVANTE, "Atividade X")

    document = GeneratedDocument(
        id=uuid4(), process_id=process_id, kind=DocumentKind.TABELA, state=GenerationState.PRONTO,
        version_number=2, requested_by=user_id, requested_at=NOW, started_at=NOW,
        finished_at=NOW, error_code=None, error_message=None, snapshot={"total": "211.00"},
        alerts=(alert,), plan_hash="a" * 64, files=(pdf,),
    )  # fmt: skip

    assert (document.process_id, document.kind, document.version_number) == (
        process_id, DocumentKind.TABELA, 2,
    )  # fmt: skip
    assert document.files == (pdf,)
    assert document.files[0] == GeneratedFile(DocumentFormat.PDF, "abc.pdf", "f" * 64, 1234)
    assert document.alerts[0].code is GenerationAlertCode.ATIVIDADE_SEM_COMPROVANTE
    assert document.snapshot == {"total": "211.00"}


def test_a_pending_generation_has_no_version_number_files_or_error():
    document = GeneratedDocument(
        id=uuid4(), process_id=uuid4(), kind=DocumentKind.COMPROVANTE,
        state=GenerationState.GERANDO, version_number=None, requested_by=uuid4(),
        requested_at=NOW,
    )  # fmt: skip

    assert document.version_number is None
    assert document.files == () and document.alerts == ()
    assert (document.started_at, document.finished_at, document.error_code) == (None, None, None)
    assert document.snapshot is None and document.plan_hash is None


def test_a_generated_version_is_immutable():
    document = GeneratedDocument(
        id=uuid4(), process_id=uuid4(), kind=DocumentKind.RELATORIO,
        state=GenerationState.PRONTO, version_number=1, requested_by=uuid4(), requested_at=NOW,
    )  # fmt: skip

    with pytest.raises(dataclasses.FrozenInstanceError):
        document.state = GenerationState.FALHOU  # type: ignore[misc]


def test_a_failed_generation_keeps_the_code_and_the_message_of_the_failure():
    document = GeneratedDocument(
        id=uuid4(), process_id=uuid4(), kind=DocumentKind.COMPROVANTE,
        state=GenerationState.FALHOU, version_number=None, requested_by=uuid4(),
        requested_at=NOW, error_code=GenerationCode.INTERROMPIDA,
        error_message="O servidor reiniciou durante a geração",
    )  # fmt: skip

    assert document.error_code is GenerationCode.INTERROMPIDA
    assert document.error_message == "O servidor reiniciou durante a geração"
    assert document.version_number is None


def test_a_wording_job_uses_the_same_states_and_keeps_its_warnings():
    warning = GenerationAlert(GenerationAlertCode.REDACAO_INDISPONIVEL, "Seção 1.1")

    job = WordingJob(
        id=uuid4(), process_id=uuid4(), section_key="1.1", state=GenerationState.PRONTO,
        requested_by=uuid4(), requested_at=NOW, started_at=NOW, finished_at=NOW,
        error_code=None, warnings=(warning,),
    )  # fmt: skip

    assert (job.section_key, job.state) == ("1.1", GenerationState.PRONTO)
    assert job.warnings == (warning,)
    assert can_transition(job.state, GenerationState.FALHOU) is False
