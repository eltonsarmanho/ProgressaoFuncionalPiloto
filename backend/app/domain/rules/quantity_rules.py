"""Quantity and hours derived by rule from extracted fields (CLS-06). Never points, never AI."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.domain.entities.activity import Level
from app.domain.entities.document import DocAlertCode
from app.domain.entities.extraction import ExtractedActivity
from app.domain.entities.extraction import TaxonomyCode as T

_HOUR_BASED = frozenset(
    {
        T.EXTENSAO_CURSO_COORDENACAO,
        T.EXTENSAO_CURSO_MINISTRANTE,
        T.EXTENSAO_EVENTO_COORDENACAO,
        T.EXTENSAO_EVENTO_MINISTRANTE,
        T.ESTAGIO_CAPACITACAO,
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


def derive_quantity(taxonomy: T, extracted: ExtractedActivity) -> QuantityResult:
    """Quantity, hours and Group I data for a taxonomy; per-year items carry an estimate warning."""
    if taxonomy is T.DISCIPLINA_MINISTRADA:
        return QuantityResult(None, extracted.hours, extracted.level, extracted.academic_period, ())
    if taxonomy in _HOUR_BASED:
        return QuantityResult(None, extracted.hours, None, None, ())
    if taxonomy in _PER_YEAR:
        years = 1
        if extracted.start_date and extracted.end_date:
            years = max(1, _whole_years(extracted.start_date, extracted.end_date))
        return QuantityResult(Decimal(years), None, None, None, (DocAlertCode.QUANTIDADE_ESTIMADA,))
    return QuantityResult(Decimal(1), None, None, None, ())
