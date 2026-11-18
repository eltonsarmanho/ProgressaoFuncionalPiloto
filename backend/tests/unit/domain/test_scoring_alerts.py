"""VERIF-13: scoring alert codes share the Alert shape of fundacao."""

from app.domain.rules.process_verification import Alert, AlertCode, Severity
from app.domain.rules.scoring_alerts import NotScoredReason, ScoringAlertCode

EXPECTED_CODES = {
    "TABELA_NAO_ENCONTRADA",
    "TABELA_DE_OUTRA_UNIDADE",
    "TABELA_PENDENTE_VALIDACAO",
    "TABELA_FORA_DE_VIGENCIA",
    "SEM_EXTENSAO_OU_PESQUISA",
    "MINIMO_NAO_DEFINIDO",
    "INTERSTICIO_PARCIAL",
    "DATA_AUSENTE",
    "DATA_FIM_AUSENTE",  # TER-05
    "SEM_COMPROVANTE",
    "PONTOS_AJUSTADOS_MANUALMENTE",
    "VALOR_UNITARIO_MANUAL",  # UIM-21
    "LIMITE_APLICADO",
    "CARGA_HORARIA_NAO_INFORMADA",
}


def test_scoring_alert_codes_are_exactly_the_design_codes():
    assert {c.name for c in ScoringAlertCode} == EXPECTED_CODES
    assert {c.value for c in ScoringAlertCode} == EXPECTED_CODES


def test_alert_accepts_a_scoring_alert_code():
    alert = Alert(
        code=ScoringAlertCode.SEM_COMPROVANTE,
        severity=Severity.ALERTA,
        message="Atividade sem comprovante.",
        norm_reference="Res. 4.644/2015-CONSEPE",
    )

    assert alert.code is ScoringAlertCode.SEM_COMPROVANTE
    assert alert.severity is Severity.ALERTA


def test_alert_still_accepts_a_fundacao_code():
    alert = Alert(AlertCode.DADOS_INCOMPLETOS, Severity.ALERTA, "m", "ref")

    assert alert.code is AlertCode.DADOS_INCOMPLETOS


def test_not_scored_reasons_are_separate_from_alert_codes():
    reasons = {r.name for r in NotScoredReason}

    assert reasons == {
        "SEM_ENQUADRAMENTO",
        "FORA_DO_INTERSTICIO",
        "DUPLICIDADE",
        "REJEITADA",
        "GRUPO_NAO_CONTA",
        "SEM_TABELA",
        "CARGA_HORARIA_INSUFICIENTE",
    }
    assert reasons.isdisjoint(EXPECTED_CODES)


def test_minimum_hours_codes_have_the_exact_names():
    assert ScoringAlertCode.CARGA_HORARIA_NAO_INFORMADA.value == "CARGA_HORARIA_NAO_INFORMADA"
    assert NotScoredReason.CARGA_HORARIA_INSUFICIENTE.value == "CARGA_HORARIA_INSUFICIENTE"


def test_missing_hours_alert_code_is_a_warning_and_the_reason_is_not_an_alert_code():
    alert = Alert(
        ScoringAlertCode.CARGA_HORARIA_NAO_INFORMADA, Severity.ALERTA, "m", "Res. 4.644/2015"
    )

    assert alert.code is ScoringAlertCode.CARGA_HORARIA_NAO_INFORMADA
    assert alert.severity is Severity.ALERTA
    assert "CARGA_HORARIA_INSUFICIENTE" not in {c.name for c in ScoringAlertCode}
