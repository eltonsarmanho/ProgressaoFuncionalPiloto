"""Generated documents, their files and the wording jobs (VER-01, VER-04, VER-05, REL-13).

A generated version is immutable once it leaves GERANDO (AD-012); the version number is only
assigned when the state becomes PRONTO.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID


class DocumentKind(StrEnum):
    TABELA = "TABELA"
    RELATORIO = "RELATORIO"
    COMPROVANTE = "COMPROVANTE"


class DocumentFormat(StrEnum):
    DOCX = "DOCX"
    PDF = "PDF"


class GenerationState(StrEnum):
    GERANDO = "GERANDO"
    PRONTO = "PRONTO"
    FALHOU = "FALHOU"


_TRANSITIONS = {
    (GenerationState.GERANDO, GenerationState.PRONTO),
    (GenerationState.GERANDO, GenerationState.FALHOU),
}


def can_transition(current: GenerationState, target: GenerationState) -> bool:
    """GERANDO -> PRONTO or FALHOU; a finished generation never changes."""
    return (current, target) in _TRANSITIONS


class GenerationCode(StrEnum):
    """Stable codes of refusals and failures (refused requests and `error_code` of a row)."""

    SEM_ATIVIDADES_VALIDADAS = "SEM_ATIVIDADES_VALIDADAS"
    TABELA_NAO_ESCOLHIDA = "TABELA_NAO_ESCOLHIDA"
    ATIVIDADE_SEM_DESCRICAO = "ATIVIDADE_SEM_DESCRICAO"
    COMPROVANTE_GRANDE_DEMAIS = "COMPROVANTE_GRANDE_DEMAIS"
    IMAGEM_GRANDE_DEMAIS = "IMAGEM_GRANDE_DEMAIS"
    ORIGINAL_INDISPONIVEL = "ORIGINAL_INDISPONIVEL"
    ORIGINAIS_EXCLUIDOS = "ORIGINAIS_EXCLUIDOS"
    INTERROMPIDA = "INTERROMPIDA"
    ESPACO_INSUFICIENTE = "ESPACO_INSUFICIENTE"
    ERRO_INTERNO = "ERRO_INTERNO"
    GERACAO_EM_ANDAMENTO = "GERACAO_EM_ANDAMENTO"
    REDACAO_EM_ANDAMENTO = "REDACAO_EM_ANDAMENTO"
    ARTEFATOS_PENDENTES = "ARTEFATOS_PENDENTES"
    CONFIRMACAO_OBRIGATORIA = "CONFIRMACAO_OBRIGATORIA"
    OPERACAO_EM_ANDAMENTO = "OPERACAO_EM_ANDAMENTO"
    CONCLUSAO_EXIGE_EXCLUSAO = "CONCLUSAO_EXIGE_EXCLUSAO"
    ARQUIVO_EXCLUIDO = "ARQUIVO_EXCLUIDO"
    PAGINA_FORA_DO_DOCUMENTO = "PAGINA_FORA_DO_DOCUMENTO"
    VERSAO_DESATUALIZADA = "VERSAO_DESATUALIZADA"
    PROCESSO_SOMENTE_LEITURA = "PROCESSO_SOMENTE_LEITURA"


class GenerationAlertCode(StrEnum):
    """Alerts that travel with a result without refusing it."""

    ATIVIDADE_SEM_COMPROVANTE = "ATIVIDADE_SEM_COMPROVANTE"
    REDACAO_REJEITADA = "REDACAO_REJEITADA"
    REDACAO_INDISPONIVEL = "REDACAO_INDISPONIVEL"
    ARRANJO_DESATUALIZADO = "ARRANJO_DESATUALIZADO"
    NUMERACAO_DIVERGENTE = "NUMERACAO_DIVERGENTE"
    ATIVIDADES_FORA_DO_DOCUMENTO = "ATIVIDADES_FORA_DO_DOCUMENTO"
    PAGINA_REPETIDA_JUSTIFICADA = "PAGINA_REPETIDA_JUSTIFICADA"
    PAGINA_RASTERIZADA = "PAGINA_RASTERIZADA"
    RASCUNHO_DESATUALIZADO = "RASCUNHO_DESATUALIZADO"
    EXCLUSAO_PARCIAL = "EXCLUSAO_PARCIAL"


@dataclass(frozen=True)
class GenerationAlert:
    code: GenerationAlertCode
    message: str = ""


@dataclass(frozen=True)
class GeneratedFile:
    format: DocumentFormat
    internal_name: str
    sha256: str
    size_bytes: int


@dataclass(frozen=True)
class GeneratedDocument:
    id: UUID
    process_id: UUID
    kind: DocumentKind
    state: GenerationState
    version_number: int | None
    requested_by: UUID
    requested_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error_code: GenerationCode | None = None
    error_message: str | None = None
    snapshot: dict[str, Any] | None = None
    alerts: tuple[GenerationAlert, ...] = ()
    plan_hash: str | None = None
    files: tuple[GeneratedFile, ...] = ()


@dataclass(frozen=True)
class WordingJob:
    """Background request to word one report section (REL-13)."""

    id: UUID
    process_id: UUID
    section_key: str
    state: GenerationState
    requested_by: UUID
    requested_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error_code: GenerationCode | None = None
    warnings: tuple[GenerationAlert, ...] = ()
