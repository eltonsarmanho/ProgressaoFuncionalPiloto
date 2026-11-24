"""Board ordinance, opinion fields and request settings (PORT-02, PORT-05, PAR-01, PAR-12, PMOD-28).

The ordinance is its own entity, not a `Document`: it never enters the activities, the score or
the Comprovante (PORT-09). Each value read from it keeps the page it came from and whether it
was extracted or typed by the person.
"""

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from uuid import UUID


class BoardRole(StrEnum):
    PRESIDENTE = "PRESIDENTE"
    MEMBRO = "MEMBRO"
    SUPLENTE = "SUPLENTE"


class ValueSource(StrEnum):
    EXTRAIDO = "EXTRAIDO"
    INFORMADO = "INFORMADO"


class ReadingState(StrEnum):
    SEM_ARQUIVO = "SEM_ARQUIVO"
    PENDENTE = "PENDENTE"
    LENDO = "LENDO"
    LIDA = "LIDA"
    FALHOU = "FALHOU"


class OpinionConclusion(StrEnum):
    FAVORAVEL = "FAVORAVEL"
    DESFAVORAVEL = "DESFAVORAVEL"


class OrdinanceReadingCode(StrEnum):
    """Why a reading of the ordinance failed (PORT-07)."""

    IA_INDISPONIVEL = "IA_INDISPONIVEL"
    IA_CREDENCIAL_RECUSADA = "IA_CREDENCIAL_RECUSADA"
    RESPOSTA_INVALIDA = "RESPOSTA_INVALIDA"
    TEXTO_ILEGIVEL = "TEXTO_ILEGIVEL"
    INTERROMPIDA = "INTERROMPIDA"
    ERRO_INTERNO = "ERRO_INTERNO"


class OrdinanceWarningCode(StrEnum):
    VALOR_SEM_ORIGEM = "VALOR_SEM_ORIGEM"
    MEMBROS_NAO_ENCONTRADOS = "MEMBROS_NAO_ENCONTRADOS"


@dataclass(frozen=True)
class OrdinanceWarning:
    code: OrdinanceWarningCode
    field: str


@dataclass(frozen=True)
class BoardMember:
    name: str
    role: BoardRole
    page: int | None
    source: ValueSource


@dataclass(frozen=True)
class OrdinanceFile:
    internal_name: str
    original_name: str
    mime: str
    size_bytes: int
    sha256: str
    page_count: int | None = None
    deleted_at: datetime | None = None


@dataclass
class BoardOrdinance:
    process_id: UUID
    number: str | None = None
    number_page: int | None = None
    number_source: ValueSource | None = None
    ordinance_date: date | None = None
    date_page: int | None = None
    date_source: ValueSource | None = None
    members: tuple[BoardMember, ...] = ()
    file: OrdinanceFile | None = None
    reading_state: ReadingState = ReadingState.SEM_ARQUIVO
    reading_code: OrdinanceReadingCode | None = None
    warnings: tuple[OrdinanceWarning, ...] = ()
    version: int = 1

    @property
    def is_registered(self) -> bool:
        """DOS-03: the ordinance counts as registered with at least one member."""
        return bool(self.members)


@dataclass
class BoardOpinion:
    """The fields the person fills for the Parecer; the conclusion has no initial value."""

    process_id: UUID
    conclusion: OpinionConclusion | None = None
    opinion_date: date | None = None
    place: str | None = None
    version: int = 1


@dataclass
class RequestSettings:
    process_id: UUID
    city: str | None = None
    version: int = 1


_READ_TRANSITIONS = {
    (ReadingState.SEM_ARQUIVO, ReadingState.PENDENTE),
    (ReadingState.PENDENTE, ReadingState.LENDO),
    (ReadingState.LENDO, ReadingState.LIDA),
    (ReadingState.LENDO, ReadingState.FALHOU),
    (ReadingState.LIDA, ReadingState.PENDENTE),
    (ReadingState.FALHOU, ReadingState.PENDENTE),
}


def can_read_transition(current: ReadingState, target: ReadingState) -> bool:
    """A reading is queued, read and finished; a finished one only goes back to the queue."""
    return (current, target) in _READ_TRANSITIONS
