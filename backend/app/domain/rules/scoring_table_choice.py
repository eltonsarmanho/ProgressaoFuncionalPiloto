"""Verification of the scoring table chosen for a process (SEL-03, SEL-05..SEL-07) and the guards
of the version in use of a unit (GTAB-03, GTAB-06, GTAB-07).

Pure functions: the verification reports alerts only and never blocks the choice.
"""

from collections.abc import Collection
from datetime import date
from uuid import UUID

from app.domain.entities.scoring import ScoringTableVersion, TableStatus
from app.domain.rules.process_verification import Alert, Severity
from app.domain.rules.scoring_alerts import ScoringAlertCode

REF_TABLE = "Res. 4.644/2015-CONSEPE, Anexo I"
NORM_OFFICIAL_TABLE = "TABELA-OFICIAL-UFPA"


def verify_table_choice(
    chosen: ScoringTableVersion | None,
    table_unit_ids: Collection[UUID],
    professor_unit_id: UUID,
    interstice_end: date,
) -> list[Alert]:
    if chosen is None:
        return [
            Alert(
                ScoringAlertCode.TABELA_NAO_ENCONTRADA,
                Severity.REQUER_ANALISE_NORMATIVA,
                "Não há versão de tabela de pontuação da unidade do docente vigente na data "
                "final do interstício; escolha uma tabela explicitamente.",
                REF_TABLE,
                NORM_OFFICIAL_TABLE,
            )
        ]
    alerts: list[Alert] = []
    if professor_unit_id not in table_unit_ids:
        alerts.append(
            Alert(
                ScoringAlertCode.TABELA_DE_OUTRA_UNIDADE,
                Severity.ALERTA,
                "A tabela escolhida pertence a outra unidade acadêmica que não a do docente.",
                chosen.norm_reference,
                chosen.norm_code,
            )
        )
    if chosen.status is TableStatus.PENDENTE_VALIDACAO:
        alerts.append(
            Alert(
                ScoringAlertCode.TABELA_PENDENTE_VALIDACAO,
                Severity.REQUER_ANALISE_NORMATIVA,
                "A tabela escolhida está pendente de validação normativa; o resultado "
                "calculado com ela exige conferência.",
                chosen.norm_reference,
                chosen.norm_code,
            )
        )
    if not chosen.covers(interstice_end):
        alerts.append(
            Alert(
                ScoringAlertCode.TABELA_FORA_DE_VIGENCIA,
                Severity.ALERTA,
                "A versão da tabela escolhida não estava vigente na data final do interstício.",
                chosen.norm_reference,
                chosen.norm_code,
            )
        )
    return alerts


def pick_unit_default(
    default_version: ScoringTableVersion | None,
    *,
    table_archived: bool,
    table_unit_ids: Collection[UUID],
    unit_id: UUID,
) -> ScoringTableVersion | None:
    """The version in use of the unit when it still passes the guards, else None (GTAB-06).

    The guards are: the version is not superseded, its table is not archived and its table is
    still associated with the unit. The validity is not asked: a version in use outside its
    validity is still suggested (GTAB-07).
    """
    if default_version is None or default_version.is_superseded:
        return None
    if table_archived or unit_id not in table_unit_ids:
        return None
    return default_version
