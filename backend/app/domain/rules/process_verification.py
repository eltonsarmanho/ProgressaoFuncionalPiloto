"""Deterministic process verification (PROC-03..PROC-11, CARR-04..CARR-07).

Pure function: never changes the snapshot, never blocks; it only reports alerts.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from app.domain.entities.career import CareerVersion, Modality, select_version
from app.domain.entities.professor import Titration, titration_at_least
from app.domain.rules.interstice import Interstice
from app.domain.rules.scoring_alerts import ScoringAlertCode

RESTRUCTURING_DATE = date(2025, 1, 1)  # Lei 15.141/2025 em vigor

REF_INTERSTICE = "Res. 4.644/2015-CONSEPE, art. 5º; Lei 12.772/2012, art. 12"
REF_COMPLETION = "Res. 4.644/2015-CONSEPE, art. 29"
REF_MODALITY = "Res. 4.644/2015-CONSEPE, art. 1º, parágrafo único; Lei 12.772/2012, art. 12"
REF_RESTRUCTURING = "Lei 15.141/2025 (Lei 12.772/2012, art. 12, §7º, e Anexo II)"
REF_NO_STRUCTURE = "Res. 4.644/2015-CONSEPE, art. 29; Lei 12.772/2012, art. 12"
REF_TITRATION = "Manual do Servidor da PROGEP, progressão e promoção"

TITRATION_NAMES = {
    Titration.GRADUACAO: "graduação",
    Titration.ESPECIALIZACAO: "especialização",
    Titration.MESTRADO: "mestrado",
    Titration.DOUTORADO: "doutorado",
}

# NLINK-03: norm codes of the rules that do not come from a career structure
NORM_RES_4644 = "RES-4644-2015-CONSEPE"
NORM_LEI_12772 = "LEI-12772-2012"


class Severity(StrEnum):
    ERRO = "ERRO"
    ALERTA = "ALERTA"
    REQUER_ANALISE_NORMATIVA = "REQUER_ANALISE_NORMATIVA"


class AlertCode(StrEnum):
    INTERSTICIO_DATAS_INVALIDAS = "INTERSTICIO_DATAS_INVALIDAS"
    INTERSTICIO_NAO_CONCLUIDO = "INTERSTICIO_NAO_CONCLUIDO"
    INTERSTICIO_CRUZA_REESTRUTURACAO = "INTERSTICIO_CRUZA_REESTRUTURACAO"
    ESTRUTURA_NAO_CADASTRADA = "ESTRUTURA_NAO_CADASTRADA"
    CLASSE_INEXISTENTE_NA_ESTRUTURA = "CLASSE_INEXISTENTE_NA_ESTRUTURA"
    DENOMINACAO_DIVERGENTE = "DENOMINACAO_DIVERGENTE"
    MODALIDADE_INCOMPATIVEL = "MODALIDADE_INCOMPATIVEL"
    INTERSTICIO_INSUFICIENTE = "INTERSTICIO_INSUFICIENTE"
    TITULACAO_INSUFICIENTE = "TITULACAO_INSUFICIENTE"


@dataclass(frozen=True)
class Alert:
    code: AlertCode | ScoringAlertCode
    severity: Severity
    message: str
    norm_reference: str
    norm_code: str | None = None  # NLINK-03: the registered norm behind the rule


@dataclass(frozen=True)
class ProcessSnapshot:
    modality: Modality
    current_class: str
    current_denomination: str
    current_level: int
    target_class: str
    target_denomination: str
    target_level: int
    start_date: date
    end_date: date
    opening_date: date


def _sides(p: ProcessSnapshot):
    return (
        ("atual", p.current_class, p.current_denomination, p.current_level),
        ("pretendida", p.target_class, p.target_denomination, p.target_level),
    )


def _structure_alerts(p: ProcessSnapshot, version: CareerVersion, dates_ok: bool) -> list[Alert]:
    alerts: list[Alert] = []

    missing = []
    for side, code, _, level in _sides(p):
        career_class = version.get_class(code)
        if career_class is None:
            missing.append(f"classe {side} {code}")
        elif level not in career_class.levels:
            missing.append(f"nível {level} da classe {side} {code}")
    if missing:
        alerts.append(
            Alert(
                AlertCode.CLASSE_INEXISTENTE_NA_ESTRUTURA,
                Severity.ERRO,
                f"Não existe na estrutura {version.name}: {'; '.join(missing)}.",
                version.norm_reference,
                version.norm_code,
            )
        )

    divergent = []
    for side, code, denomination, _ in _sides(p):
        career_class = version.get_class(code)
        normalized = (denomination or "").strip().casefold()
        if career_class and normalized not in {d.casefold() for d in career_class.denominations}:
            expected = " ou ".join(career_class.denominations)
            divergent.append(
                f"classe {side} {code}: informada \"{denomination}\", esperada \"{expected}\""
            )
    if divergent:
        alerts.append(
            Alert(
                AlertCode.DENOMINACAO_DIVERGENTE,
                Severity.ALERTA,
                f"Denominação divergente na estrutura {version.name}: {'; '.join(divergent)}.",
                version.norm_reference,
                version.norm_code,
            )
        )

    if p.modality is Modality.PROMOCAO:
        current = version.get_class(p.current_class)
        target = version.get_class(p.target_class)
        following = version.next_class(p.current_class)
        compatible = (
            current is not None
            and target is not None
            and following is not None
            and following.code == target.code
            and p.current_level == current.levels[-1]
            and p.target_level == target.levels[0]
        )
        if not compatible:
            alerts.append(
                Alert(
                    AlertCode.MODALIDADE_INCOMPATIVEL,
                    Severity.ALERTA,
                    "A promoção informada não segue a sequência usual (último nível da classe "
                    "atual para o primeiro nível da classe seguinte); confira a norma que "
                    "fundamenta o salto.",
                    REF_MODALITY,
                    NORM_LEI_12772,
                )
            )

    minimum = version.min_months(p.modality, p.target_class)
    if dates_ok and minimum is not None:
        months = Interstice(p.start_date, p.end_date).months()
        if months < minimum:
            alerts.append(
                Alert(
                    AlertCode.INTERSTICIO_INSUFICIENTE,
                    Severity.ERRO,
                    f"Interstício de {months} meses; o mínimo exigido é de {minimum} meses.",
                    version.norm_reference,
                    version.norm_code,
                )
            )
    return alerts


def _titration_alert(
    p: ProcessSnapshot, version: CareerVersion, titration: Titration | None
) -> Alert | None:
    """NTIT-01..05: only a change of class is checked, against the target class rule."""
    if titration is None or p.target_class == p.current_class:
        return None
    target = version.get_class(p.target_class)
    required = target.required_titration if target else None
    if required is None or titration_at_least(titration, required):
        return None
    return Alert(
        AlertCode.TITULACAO_INSUFICIENTE,
        Severity.ALERTA,
        f"A classe {p.target_class} ({p.target_denomination}) exige "
        f"{TITRATION_NAMES[required]}; a titulação cadastrada do docente é "
        f"{TITRATION_NAMES[titration]}.",
        REF_TITRATION,
        version.required_titration_norm_code,
    )


def verify_process(
    p: ProcessSnapshot,
    versions: Sequence[CareerVersion],
    titration: Titration | None = None,
) -> list[Alert]:
    alerts: list[Alert] = []
    interstice = Interstice(p.start_date, p.end_date)
    dates_ok = p.end_date > p.start_date

    if not dates_ok:
        alerts.append(
            Alert(
                AlertCode.INTERSTICIO_DATAS_INVALIDAS,
                Severity.ERRO,
                "A data final do interstício deve ser posterior à data inicial.",
                REF_INTERSTICE,
                NORM_RES_4644,
            )
        )
    if p.end_date > p.opening_date:
        alerts.append(
            Alert(
                AlertCode.INTERSTICIO_NAO_CONCLUIDO,
                Severity.ALERTA,
                "A data final do interstício é posterior à data de abertura do processo.",
                REF_COMPLETION,
                NORM_RES_4644,
            )
        )
    if interstice.crosses(RESTRUCTURING_DATE):
        alerts.append(
            Alert(
                AlertCode.INTERSTICIO_CRUZA_REESTRUTURACAO,
                Severity.REQUER_ANALISE_NORMATIVA,
                "O interstício começa antes de 01/01/2025 e termina depois da reestruturação "
                "da carreira pela Lei 15.141/2025; o enquadramento exige análise normativa.",
                REF_RESTRUCTURING,
                NORM_LEI_12772,
            )
        )

    version = select_version(versions, p.end_date)
    if version is None:
        alerts.append(
            Alert(
                AlertCode.ESTRUTURA_NAO_CADASTRADA,
                Severity.REQUER_ANALISE_NORMATIVA,
                "Não há estrutura de carreira cadastrada vigente na data final do interstício.",
                REF_NO_STRUCTURE,
                NORM_RES_4644,
            )
        )
    else:
        alerts.extend(_structure_alerts(p, version, dates_ok))
        titration_alert = _titration_alert(p, version, titration)
        if titration_alert is not None:
            alerts.append(titration_alert)

    if p.modality is Modality.PROGRESSAO and (
        p.target_class != p.current_class or p.target_level != p.current_level + 1
    ):
        alerts.append(
            Alert(
                AlertCode.MODALIDADE_INCOMPATIVEL,
                Severity.ALERTA,
                "A progressão informada não segue a sequência usual (um nível acima, na mesma "
                "classe); confira a norma que fundamenta o salto.",
                REF_MODALITY,
                NORM_LEI_12772,
            )
        )
    return alerts
