"""NTIT-01..05, NTIT-07 and the titration edge cases, on synthetic career structures."""

from dataclasses import replace
from datetime import date

import pytest

from app.domain.entities.career import CareerClass, CareerVersion, Modality
from app.domain.entities.professor import Titration
from app.domain.rules.process_verification import (
    AlertCode,
    ProcessSnapshot,
    Severity,
    verify_process,
)

RULE_CODE = "NORMA-SINTETICA-TITULACAO"
REF_TITRATION = "Manual do Servidor da PROGEP, progressão e promoção"

SYNTHETIC_OLD = CareerVersion(
    name="Estrutura sintética antiga",
    valid_from=None,
    valid_to=date(2024, 12, 31),
    norm_reference="Norma sintética antiga, art. 1º",
    classes=(
        CareerClass("A", ("Assistente",), (1,), None),
        CareerClass("B", ("Adjunto",), (1, 2, 3, 4), 24),
        CareerClass("C", ("Associado",), (1, 2, 3, 4), 24),
    ),
)
SYNTHETIC_NEW = CareerVersion(
    name="Estrutura sintética nova",
    valid_from=date(2025, 1, 1),
    valid_to=None,
    norm_reference="Norma sintética nova, art. 1º",
    classes=(
        CareerClass("A", ("Assistente",), (1,), None),
        CareerClass("B", ("Adjunto",), (1, 2, 3, 4), 24),
        CareerClass("C", ("Associado",), (1, 2, 3, 4), 24, Titration.DOUTORADO),
        CareerClass("D", ("Titular",), (1,), 24, Titration.DOUTORADO),
    ),
    norm_code="NORMA-SINTETICA-ESTRUTURA",
    required_titration_norm_code=RULE_CODE,
)
SYNTHETIC_VERSIONS = (SYNTHETIC_OLD, SYNTHETIC_NEW)

PROMOTION_B_C = ProcessSnapshot(
    modality=Modality.PROMOCAO,
    current_class="B",
    current_denomination="Adjunto",
    current_level=4,
    target_class="C",
    target_denomination="Associado",
    target_level=1,
    start_date=date(2025, 2, 1),
    end_date=date(2027, 2, 1),
    opening_date=date(2027, 3, 1),
    notes="Observação de teste",
    resp_name="Responsável de Teste",
    resp_position="Diretor",
    resp_appointment="Portaria 1/2025",
    resp_admin_unit="Faculdade de Teste",
)

EXPECTED_MESSAGE = (
    "A classe C (Associado) exige doutorado; a titulação cadastrada do docente é mestrado."
)


def titration_alerts(snapshot, titration, versions=SYNTHETIC_VERSIONS):
    alerts = verify_process(snapshot, versions, titration)
    return [a for a in alerts if a.code is AlertCode.TITULACAO_INSUFICIENTE]


# NTIT-01, NTIT-02, NTIT-07
def test_mestrado_promoted_b_to_c_in_synthetic_structure_gets_the_alert():
    [alert] = titration_alerts(PROMOTION_B_C, Titration.MESTRADO)
    assert alert.severity is Severity.ALERTA
    assert alert.message == EXPECTED_MESSAGE
    assert alert.norm_reference == REF_TITRATION
    assert alert.norm_code == RULE_CODE


def test_full_alert_list_of_synthetic_promotion_is_only_the_titration_alert():
    alerts = verify_process(PROMOTION_B_C, SYNTHETIC_VERSIONS, Titration.MESTRADO)
    assert [(a.code, a.severity) for a in alerts] == [
        (AlertCode.TITULACAO_INSUFICIENTE, Severity.ALERTA)
    ]


@pytest.mark.parametrize(
    ("titration", "name"),
    [(Titration.GRADUACAO, "graduação"), (Titration.ESPECIALIZACAO, "especialização")],
)
def test_lower_titrations_are_named_in_lowercase_in_synthetic_structure(titration, name):
    [alert] = titration_alerts(PROMOTION_B_C, titration)
    assert alert.message == (
        f"A classe C (Associado) exige doutorado; a titulação cadastrada do docente é {name}."
    )


# NTIT-03
def test_doutorado_gets_no_alert_in_synthetic_structure():
    assert titration_alerts(PROMOTION_B_C, Titration.DOUTORADO) == []


# NTIT-04
def test_progression_c1_c2_with_mestrado_is_not_checked_in_synthetic_structure():
    progression = replace(
        PROMOTION_B_C,
        modality=Modality.PROGRESSAO,
        current_class="C",
        current_denomination="Associado",
        current_level=1,
        target_level=2,
    )
    assert titration_alerts(progression, Titration.MESTRADO) == []


# The target class differs from the current one: a jump A1 -> C1 is also checked
def test_jump_a1_c1_with_mestrado_gets_the_alert_in_synthetic_structure():
    jump = replace(PROMOTION_B_C, current_class="A", current_denomination="Assistente",
                   current_level=1)
    [alert] = titration_alerts(jump, Titration.MESTRADO)
    assert alert.message == EXPECTED_MESSAGE
    assert alert.severity is Severity.ALERTA


# NTIT-05
def test_class_without_rule_gets_no_alert_in_synthetic_structure():
    to_b = replace(
        PROMOTION_B_C,
        current_class="A",
        current_denomination="Assistente",
        current_level=1,
        target_class="B",
        target_denomination="Adjunto",
    )
    assert titration_alerts(to_b, Titration.GRADUACAO) == []


def test_structure_without_any_rule_gets_no_alert_synthetic_old():
    old = replace(PROMOTION_B_C, start_date=date(2022, 1, 1), end_date=date(2024, 1, 1),
                  opening_date=date(2024, 2, 1))
    assert titration_alerts(old, Titration.GRADUACAO) == []


# Edge case: titration not registered
def test_titration_none_gets_no_alert_in_synthetic_structure():
    assert titration_alerts(PROMOTION_B_C, None) == []


def test_current_calls_without_titration_get_no_alert_in_synthetic_structure():
    alerts = verify_process(PROMOTION_B_C, SYNTHETIC_VERSIONS)
    assert AlertCode.TITULACAO_INSUFICIENTE not in [a.code for a in alerts]


# Edge case: interstice crossing 01/01/2025 uses the structure of the end date
def test_interstice_crossing_restructuring_uses_end_structure_synthetic():
    crossing = replace(PROMOTION_B_C, start_date=date(2024, 6, 1), end_date=date(2026, 6, 1),
                       opening_date=date(2026, 7, 1))
    alerts = verify_process(crossing, SYNTHETIC_VERSIONS, Titration.MESTRADO)
    codes = [a.code for a in alerts]
    assert AlertCode.INTERSTICIO_CRUZA_REESTRUTURACAO in codes
    [alert] = [a for a in alerts if a.code is AlertCode.TITULACAO_INSUFICIENTE]
    assert alert.norm_code == RULE_CODE

    # the same crossing judged by an end-date structure without the rule gives no alert
    no_rule_at_end = (SYNTHETIC_OLD, replace(SYNTHETIC_NEW, classes=SYNTHETIC_OLD.classes))
    assert titration_alerts(crossing, Titration.MESTRADO, no_rule_at_end) == []
