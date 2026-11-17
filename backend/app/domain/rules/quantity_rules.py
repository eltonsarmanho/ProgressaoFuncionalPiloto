"""Quantity and hours derived by rule from extracted fields (CLS-06). Never points, never AI."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.domain.entities.activity import Level
from app.domain.entities.document import DocAlertCode
from app.domain.entities.extraction import ExtractedActivity
from app.domain.entities.extraction import TaxonomyCode as T
from app.domain.rules.interstice import Interstice

_HOUR_BASED = frozenset({T.ESTAGIO_CAPACITACAO})
# One per document; the extracted hours are kept for the minimum course load check (MAP-04).
_PER_DOCUMENT_WITH_HOURS = frozenset(
    {
        T.EXTENSAO_CURSO_COORDENACAO,
        T.EXTENSAO_CURSO_MINISTRANTE,
        T.EXTENSAO_EVENTO_COORDENACAO,
        T.EXTENSAO_EVENTO_MINISTRANTE,
    }
)
_PER_YEAR = frozenset(
    {
        T.EXTENSAO_PROJETO_COORDENACAO,
        T.EXTENSAO_PROJETO_PARTICIPACAO,
        T.PESQUISA_GRUPO_COORDENACAO,
        T.PESQUISA_GRUPO_MEMBRO,
        T.PESQUISA_BOLSA_PRODUTIVIDADE,
        T.FUNCAO_DIRETOR_FACULDADE,
        T.FUNCAO_VICE_DIRETOR_FACULDADE,
        T.FUNCAO_COORDENADOR_CURSO_GRADUACAO,
        T.COLEGIADO_MEMBRO,
        T.CONSULTORIA_AD_HOC,
    }
)


@dataclass(frozen=True)
class QuantityResult:
    quantity: Decimal | None
    hours: Decimal | None
    level: Level | None
    academic_period: str | None
    warnings: tuple[DocAlertCode, ...]


def _whole_years(start: date, end: date) -> int:
    years = end.year - start.year
    if (end.month, end.day) < (start.month, start.day):
        years -= 1
    return years


def _exercise_years(extracted: ExtractedActivity, interstice: Interstice | None) -> int:
    """Complete years of exercise, inside the interstice when given; 0 when unknown (REAL-11)."""
    start, end = extracted.start_date, extracted.end_date
    if start is None or end is None or end < start:
        return 0
    if interstice is not None:
        start, end = max(start, interstice.start), min(end, interstice.end)
        if end < start:
            return 0
    return _whole_years(start, end)


def derive_quantity(
    taxonomy: T, extracted: ExtractedActivity, interstice: Interstice | None = None
) -> QuantityResult:
    """Quantity, hours and Group I data for a taxonomy; per-year items carry an estimate warning.

    A per-year item counts the complete years of the period inside the interstice, never
    rounded up. With less than a year, or without both dates, the quantity is 0 and the
    QUANTIDADE_ESTIMADA warning asks the user to inform it (the engine reads an empty quantity
    as 1, so 0 is the value that does not inflate the potential).
    """
    if taxonomy is T.DISCIPLINA_MINISTRADA:
        return QuantityResult(None, extracted.hours, extracted.level, extracted.academic_period, ())
    if taxonomy in _HOUR_BASED:
        return QuantityResult(None, extracted.hours, None, None, ())
    if taxonomy in _PER_DOCUMENT_WITH_HOURS:
        return QuantityResult(Decimal(1), extracted.hours, None, None, ())
    if taxonomy in _PER_YEAR:
        years = _exercise_years(extracted, interstice)
        return QuantityResult(Decimal(years), None, None, None, (DocAlertCode.QUANTIDADE_ESTIMADA,))
    return QuantityResult(Decimal(1), None, None, None, ())
