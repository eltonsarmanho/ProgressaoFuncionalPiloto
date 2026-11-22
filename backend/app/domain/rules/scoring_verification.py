"""Process-level scoring verification (VERIF-09..VERIF-13).

Pure functions: they report alerts and a comparison with the reference minimum; they never
change data and never block.
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from app.domain.entities.career import CareerVersion
from app.domain.entities.professor import WorkRegime
from app.domain.entities.scoring import ScoringTableVersion
from app.domain.rules.process_verification import Alert, Severity
from app.domain.rules.scoring_alerts import ScoringAlertCode
from app.domain.rules.scoring_engine import ScoringResult

REF_EXTENSION_RESEARCH = "Res. 4.644/2015-CONSEPE, art. 13, II"
REF_MINIMUM = "Res. 4.644/2015-CONSEPE, art. 12"
RES_4644_PREFIX = "Res. 4.644"
NORM_RES_4644 = "RES-4644-2015-CONSEPE"


class MinimumStatus(StrEnum):
    ATINGE = "ATINGE"
    NAO_ATINGE = "NAO_ATINGE"
    NAO_DEFINIDO = "NAO_DEFINIDO"


@dataclass(frozen=True)
class MinimumComparison:
    status: MinimumStatus
    minimum: Decimal | None
    total: Decimal


@dataclass(frozen=True)
class ScoringContext:
    work_regime: WorkRegime
    current_class: str
    career_version: CareerVersion | None
    table_version: ScoringTableVersion


def reference_minimum(
    version: ScoringTableVersion,
    current_class: str,
    career_version: CareerVersion | None,
    total: Decimal,
) -> MinimumComparison:
    undefined = MinimumComparison(MinimumStatus.NAO_DEFINIDO, None, total)
    if career_version is None or not career_version.name.startswith(RES_4644_PREFIX):
        return undefined
    by_class = (version.minimums or {}).get("by_current_class", {})
    if current_class not in by_class:
        return undefined
    minimum = Decimal(str(by_class[current_class]))
    status = MinimumStatus.ATINGE if total >= minimum else MinimumStatus.NAO_ATINGE
    return MinimumComparison(status, minimum, total)


def verify_scoring(ctx: ScoringContext, result: ScoringResult) -> list[Alert]:
    alerts: list[Alert] = []
    if ctx.work_regime in (WorkRegime.DE, WorkRegime.H40):
        subtotals = result.group_subtotals
        if subtotals.get(4, Decimal(0)) + subtotals.get(5, Decimal(0)) == 0:
            alerts.append(
                Alert(
                    ScoringAlertCode.SEM_EXTENSAO_OU_PESQUISA,
                    Severity.ALERTA,
                    "Docente em regime DE ou 40 h sem pontos nos Grupos IV (extensão) e V "
                    "(pesquisa); a norma exige atividade de extensão ou pesquisa.",
                    REF_EXTENSION_RESEARCH,
                    NORM_RES_4644,
                )
            )
    comparison = reference_minimum(
        ctx.table_version, ctx.current_class, ctx.career_version, result.total
    )
    if comparison.status is MinimumStatus.NAO_DEFINIDO:
        alerts.append(
            Alert(
                ScoringAlertCode.MINIMO_NAO_DEFINIDO,
                Severity.REQUER_ANALISE_NORMATIVA,
                "O mínimo de pontos de referência não está definido para a estrutura de "
                "carreira deste processo; a comparação exige análise normativa.",
                REF_MINIMUM,
                NORM_RES_4644,
            )
        )
    return alerts
