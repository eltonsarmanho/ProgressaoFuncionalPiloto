"""Document entities, processing status and alert codes (PIPE-02, DOC-01)."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID


class DocumentStatus(StrEnum):
    PENDENTE = "PENDENTE"
    PROCESSANDO = "PROCESSANDO"
    PROCESSADO = "PROCESSADO"
    REQUER_REVISAO = "REQUER_REVISAO"
    EXTRAIDO_SEM_IA = "EXTRAIDO_SEM_IA"
    FALHOU = "FALHOU"


_FINAL = (
    DocumentStatus.PROCESSADO,
    DocumentStatus.REQUER_REVISAO,
    DocumentStatus.EXTRAIDO_SEM_IA,
    DocumentStatus.FALHOU,
)

# Reprocessing and replacement start a NEW run, so every final status may go back to
# PENDENTE. Every other pair is refused.
_TRANSITIONS = {(DocumentStatus.PENDENTE, DocumentStatus.PROCESSANDO)}
_TRANSITIONS |= {(DocumentStatus.PROCESSANDO, final) for final in _FINAL}
_TRANSITIONS |= {(final, DocumentStatus.PENDENTE) for final in _FINAL}


def can_transition(current: DocumentStatus, target: DocumentStatus) -> bool:
    """PENDENTE -> PROCESSANDO -> a final status; a final status -> PENDENTE (new run)."""
    return (current, target) in _TRANSITIONS


class DocAlertCode(StrEnum):
    SEM_ITEM_DE_PONTUACAO = "SEM_ITEM_DE_PONTUACAO"
    TEXTO_ILEGIVEL = "TEXTO_ILEGIVEL"
    DOCENTE_DIVERGENTE = "DOCENTE_DIVERGENTE"
    RESPOSTA_INVALIDA = "RESPOSTA_INVALIDA"
    NAO_ENCONTRADO_NO_TEXTO = "NAO_ENCONTRADO_NO_TEXTO"
    TRUNCADO = "TRUNCADO"
    NENHUMA_ATIVIDADE_ENCONTRADA = "NENHUMA_ATIVIDADE_ENCONTRADA"
    IA_CREDENCIAL_RECUSADA = "IA_CREDENCIAL_RECUSADA"
    IA_INDISPONIVEL = "IA_INDISPONIVEL"
    TEMPO_ESGOTADO = "TEMPO_ESGOTADO"
    QUANTIDADE_ESTIMADA = "QUANTIDADE_ESTIMADA"
    ATIVIDADE_REPETIDA = "ATIVIDADE_REPETIDA"
    TENTATIVAS_ESGOTADAS = "TENTATIVAS_ESGOTADAS"
    DATA_PARCIAL = "DATA_PARCIAL"
    DATA_FIM_DERIVADA = "DATA_FIM_DERIVADA"
    DATA_FIM_AUSENTE = "DATA_FIM_AUSENTE"
    INDEXACAO_NAO_COMPROVADA = "INDEXACAO_NAO_COMPROVADA"
    CLAUSULA_DE_DISPENSA = "CLAUSULA_DE_DISPENSA"
    ENQUADRADO_COMO_CAPACITACAO = "ENQUADRADO_COMO_CAPACITACAO"
    DOCUMENTO_FORA_DO_INTERSTICIO = "DOCUMENTO_FORA_DO_INTERSTICIO"


class TextMethod(StrEnum):
    TEXTO = "TEXTO"
    OCR = "OCR"


class RunStatus(StrEnum):
    ATIVA = "ATIVA"
    SUBSTITUIDA = "SUBSTITUIDA"


@dataclass
class Document:
    id: UUID
    process_id: UUID
    original_name: str
    internal_name: str
    mime: str
    size_bytes: int
    sha256: str
    page_count: int
    uploaded_by: UUID
    status: DocumentStatus = DocumentStatus.PENDENTE
    status_code: str | None = None
    manual_type: str | None = None
    manual_category: str | None = None
    suggested_type: str | None = None
    suggested_category: str | None = None
    confidence: Decimal | None = None
    uploaded_at: datetime | None = None
    version: int = 1
    # Set by the database on every change; read only, so it takes no part in equality.
    updated_at: datetime | None = field(default=None, compare=False)
    # Set once by the conclusion when the file is removed (DEL-05); the repository never writes
    # it from an entity, only `mark_file_deleted` does.
    file_deleted_at: datetime | None = None


@dataclass(frozen=True)
class PageText:
    document_id: UUID
    run_id: UUID
    page_number: int
    method: TextMethod
    char_count: int
    ocr_confidence: Decimal | None
    text: str


@dataclass
class ExtractionRun:
    id: UUID
    document_id: UUID
    model: str
    duration_ms: int
    raw_json: dict[str, Any]
    warnings: tuple[str, ...] = ()
    status: RunStatus = RunStatus.ATIVA
    created_at: datetime | None = field(default=None)
