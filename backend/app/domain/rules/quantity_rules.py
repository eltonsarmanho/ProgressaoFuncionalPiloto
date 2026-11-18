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
# Items whose unit in the official table (`ufpa.json`) is "por ano ...". Every other taxonomy is
# one per activity: "por ação" (IV.1 and IV.2 included), "por banca", "por aluno", "por unidade"
# and "no interstício". The test `test_quantity_rules_units` pins both lists to the table.
_PER_YEAR = frozenset(
    {
        T.PESQUISA_PROJETO_COORDENACAO,
        T.PESQUISA_GRUPO_COORDENACAO,
        T.PESQUISA_GRUPO_MEMBRO,
        T.PESQUISA_BOLSA_PRODUTIVIDADE,
        T.FUNCAO_DIRETOR_FACULDADE,
        T.FUNCAO_VICE_DIRETOR_FACULDADE,
        T.FUNCAO_COORDENADOR_CURSO_GRADUACAO,
        T.COMISSAO_ADMINISTRACAO_SUPERIOR,
        T.COMISSAO_NDE_MEMBRO,
        T.COMISSAO_UNIDADE,
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


def is_per_year(taxonomy: T) -> bool:
    """Whether the quantity of the taxonomy counts years of exercise."""
    return taxonomy in _PER_YEAR


def is_open_ended(extracted: ExtractedActivity) -> bool:
    """A start date with neither an end date nor a single event date (SEG-02)."""
    return (
        extracted.start_date is not None
        and extracted.end_date is None
        and extracted.event_date is None
    )


def _whole_years(start: date, end: date) -> int:
    years = end.year - start.year
    if (end.month, end.day) < (start.month, start.day):
        years -= 1
    return years


def _exercise_years(extracted: ExtractedActivity, interstice: Interstice | None) -> int:
    """Complete years of exercise, inside the interstice when given; 0 when unknown (REAL-11).

    Without an end date the period is open: it runs to the end of the interstice (SEG-02).
    """
    start, end = extracted.start_date, extracted.end_date
    if end is None and interstice is not None:
        end = interstice.end
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

    The quantity follows the unit of the item in the official table: one per action or per
    document for "por ação" and the other per-event units (an extension project is one action,
    whatever its length), hours for hour-based items (VER-12).

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
        warnings = [DocAlertCode.QUANTIDADE_ESTIMADA]
        if is_open_ended(extracted):
            warnings.append(DocAlertCode.DATA_FIM_AUSENTE)
        return QuantityResult(Decimal(years), None, None, None, tuple(warnings))
    return QuantityResult(Decimal(1), None, None, None, ())
