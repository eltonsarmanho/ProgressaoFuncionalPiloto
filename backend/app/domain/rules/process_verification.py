"""Deterministic process verification (PROC-03..PROC-11, CARR-04..CARR-07).

Pure function: never changes the snapshot, never blocks; it only reports alerts.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from app.domain.entities.career import CareerVersion, Modality, select_version
from app.domain.rules.interstice import Interstice
from app.domain.rules.scoring_alerts import ScoringAlertCode

RESTRUCTURING_DATE = date(2025, 1, 1)  # Lei 15.141/2025 em vigor

REF_INTERSTICE = "Res. 4.644/2015-CONSEPE, art. 5º; Lei 12.772/2012, art. 12"
REF_COMPLETION = "Res. 4.644/2015-CONSEPE, art. 29"
REF_MODALITY = "Res. 4.644/2015-CONSEPE, art. 1º, parágrafo único; Lei 12.772/2012, art. 12"
REF_RESTRUCTURING = "Lei 15.141/2025 (Lei 12.772/2012, art. 12, §7º, e Anexo II)"
REF_NO_STRUCTURE = "Res. 4.644/2015-CONSEPE, art. 29; Lei 12.772/2012, art. 12"
REF_INCOMPLETE = "Res. 4.644/2015-CONSEPE"


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
    DADOS_INCOMPLETOS = "DADOS_INCOMPLETOS"


@dataclass(frozen=True)
class Alert:
    code: AlertCode | ScoringAlertCode
    severity: Severity
    message: str
    norm_reference: str


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
    notes: str | None = None
    resp_name: str | None = None
    resp_position: str | None = None
    resp_appointment: str | None = None
    resp_admin_unit: str | None = None


OPTIONAL_FIELDS = (
    ("notes", "observações"),
    ("resp_name", "nome do responsável"),
    ("resp_position", "cargo do responsável"),
    ("resp_appointment", "portaria de designação do responsável"),
    ("resp_admin_unit", "unidade administrativa responsável"),
)


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
                    Severity.ERRO,
                    "Promoção exige passar do último nível da classe atual para o primeiro "
                    "nível da classe imediatamente seguinte.",
                    REF_MODALITY,
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
                )
            )
    return alerts


def verify_process(p: ProcessSnapshot, versions: Sequence[CareerVersion]) -> list[Alert]:
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
            )
        )
    if p.end_date > p.opening_date:
        alerts.append(
            Alert(
                AlertCode.INTERSTICIO_NAO_CONCLUIDO,
                Severity.ALERTA,
                "A data final do interstício é posterior à data de abertura do processo.",
                REF_COMPLETION,
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
            )
        )
    else:
        alerts.extend(_structure_alerts(p, version, dates_ok))

    if p.modality is Modality.PROGRESSAO and (
        p.target_class != p.current_class or p.target_level != p.current_level + 1
    ):
        alerts.append(
            Alert(
                AlertCode.MODALIDADE_INCOMPATIVEL,
                Severity.ERRO,
                "Progressão exige permanecer na mesma classe e avançar exatamente um nível.",
                REF_MODALITY,
            )
        )

    empty = [label for field, label in OPTIONAL_FIELDS if not (getattr(p, field) or "").strip()]
    if empty:
        alerts.append(
            Alert(
                AlertCode.DADOS_INCOMPLETOS,
                Severity.ALERTA,
                f"Campos não preenchidos: {', '.join(empty)}.",
                REF_INCOMPLETE,
            )
        )
    return alerts
