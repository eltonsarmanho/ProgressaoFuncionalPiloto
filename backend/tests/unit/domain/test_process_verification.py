"""PROC-03..PROC-11, CARR-04..CARR-07 and the DADOS_INCOMPLETOS edge case."""

import copy
from dataclasses import replace
from datetime import date

import pytest

from app.domain.entities.career import Modality, select_version
from app.domain.rules.career_catalog import (
    LEI_15141_2025,
    MAGISTERIO_SUPERIOR_VERSIONS,
    RES_4644_2015,
)
from app.domain.rules.interstice import Interstice
from app.domain.rules.process_verification import (
    AlertCode,
    ProcessSnapshot,
    Severity,
    verify_process,
)

VERSIONS = MAGISTERIO_SUPERIOR_VERSIONS

INSTITUTIONAL = dict(
    notes="Observação de teste",
    resp_name="Responsável de Teste",
    resp_position="Diretor",
    resp_appointment="Portaria 1/2025",
    resp_admin_unit="Faculdade de Teste",
)

# PROC-10: FASI 2022-2024
FASI_2022_2024 = ProcessSnapshot(
    modality=Modality.PROMOCAO,
    current_class="C",
    current_denomination="Adjunto",
    current_level=4,
    target_class="D",
    target_denomination="Associado",
    target_level=1,
    start_date=date(2022, 11, 23),
    end_date=date(2024, 11, 23),
    opening_date=date(2025, 3, 10),
    **INSTITUTIONAL,
)

# PROC-11: Requerimento 2024-2026, as written, all optional fields filled
REQUERIMENTO_2024_2026 = ProcessSnapshot(
    modality=Modality.PROMOCAO,
    current_class="D",
    current_denomination="Associado",
    current_level=4,
    target_class="D",
    target_denomination="Associado",
    target_level=2,
    start_date=date(2024, 11, 23),
    end_date=date(2026, 11, 23),
    opening_date=date(2026, 11, 16),
    **INSTITUTIONAL,
)

# A clean case under the new structure: progression B1 -> B2, 2025-2027
CLEAN_NEW = ProcessSnapshot(
    modality=Modality.PROGRESSAO,
    current_class="B",
    current_denomination="Adjunto",
    current_level=1,
    target_class="B",
    target_denomination="Adjunto",
    target_level=2,
    start_date=date(2025, 2, 1),
    end_date=date(2027, 2, 1),
    opening_date=date(2027, 3, 1),
    **INSTITUTIONAL,
)


def codes(alerts):
    return [a.code for a in alerts]


def find(alerts, code):
    matches = [a for a in alerts if a.code is code]
    assert len(matches) == 1, f"expected one {code}, got {codes(alerts)}"
    return matches[0]


def test_clean_case_has_no_alerts():
    assert verify_process(CLEAN_NEW, VERSIONS) == []


# PROC-05
@pytest.mark.parametrize("end", [date(2025, 2, 1), date(2025, 1, 15)])
def test_end_on_or_before_start_is_error(end):
    alerts = verify_process(replace(CLEAN_NEW, end_date=end), VERSIONS)
    alert = find(alerts, AlertCode.INTERSTICIO_DATAS_INVALIDAS)
    assert alert.severity is Severity.ERRO


# PROC-06
def test_end_after_opening_is_alert():
    alerts = verify_process(replace(CLEAN_NEW, opening_date=date(2027, 1, 31)), VERSIONS)
    alert = find(alerts, AlertCode.INTERSTICIO_NAO_CONCLUIDO)
    assert alert.severity is Severity.ALERTA


def test_end_equal_to_opening_is_not_alert():
    alerts = verify_process(replace(CLEAN_NEW, opening_date=date(2027, 2, 1)), VERSIONS)
    assert AlertCode.INTERSTICIO_NAO_CONCLUIDO not in codes(alerts)


# PROC-07
@pytest.mark.parametrize(
    "changes",
    [
        dict(target_class="C", target_denomination="Associado", target_level=2),
        dict(target_level=3),
        dict(target_level=1),
    ],
)
def test_progression_must_keep_class_and_advance_one_level(changes):
    alerts = verify_process(replace(CLEAN_NEW, **changes), VERSIONS)
    alert = find(alerts, AlertCode.MODALIDADE_INCOMPATIVEL)
    assert alert.severity is Severity.ERRO


# PROC-08
PROMO_NEW = replace(
    CLEAN_NEW,
    modality=Modality.PROMOCAO,
    current_class="C",
    current_denomination="Associado",
    current_level=4,
    target_class="D",
    target_denomination="Titular",
    target_level=1,
)


def test_valid_promotion_has_no_alerts():
    assert verify_process(PROMO_NEW, VERSIONS) == []


@pytest.mark.parametrize(
    "changes",
    [
        dict(current_class="B", current_denomination="Adjunto"),  # D is not next of B
        dict(current_level=3),  # current level is not the last of C
        dict(
            current_class="B",
            current_denomination="Adjunto",
            target_class="C",
            target_denomination="Associado",
            target_level=2,
        ),  # target level is not the first of C
    ],
)
def test_promotion_rules(changes):
    alerts = verify_process(replace(PROMO_NEW, **changes), VERSIONS)
    alert = find(alerts, AlertCode.MODALIDADE_INCOMPATIVEL)
    assert alert.severity is Severity.ERRO


# PROC-09
def test_promotion_to_class_b_requires_36_months_in_new_structure():
    snapshot = replace(
        CLEAN_NEW,
        modality=Modality.PROMOCAO,
        current_class="A",
        current_denomination="Assistente",
        current_level=1,
        target_class="B",
        target_denomination="Adjunto",
        target_level=1,
    )
    alerts = verify_process(snapshot, VERSIONS)
    alert = find(alerts, AlertCode.INTERSTICIO_INSUFICIENTE)
    assert alert.severity is Severity.ERRO
    assert "24" in alert.message
    assert "36" in alert.message
    assert codes(alerts) == [AlertCode.INTERSTICIO_INSUFICIENTE]


def test_progression_with_23_months_is_insufficient():
    alerts = verify_process(replace(CLEAN_NEW, end_date=date(2027, 1, 31)), VERSIONS)
    alert = find(alerts, AlertCode.INTERSTICIO_INSUFICIENTE)
    assert alert.severity is Severity.ERRO
    assert "23" in alert.message
    assert "24" in alert.message


# CARR-04
@pytest.mark.parametrize(
    "changes",
    [
        dict(current_class="F", target_class="F"),
        dict(target_level=5, current_level=4),
    ],
)
def test_class_or_level_missing_in_structure_is_error(changes):
    alerts = verify_process(replace(CLEAN_NEW, **changes), VERSIONS)
    alert = find(alerts, AlertCode.CLASSE_INEXISTENTE_NA_ESTRUTURA)
    assert alert.severity is Severity.ERRO


# CARR-05
def test_interstice_crossing_restructuring_requires_normative_analysis():
    snapshot = replace(CLEAN_NEW, start_date=date(2024, 12, 1), end_date=date(2027, 2, 1))
    alerts = verify_process(snapshot, VERSIONS)
    alert = find(alerts, AlertCode.INTERSTICIO_CRUZA_REESTRUTURACAO)
    assert alert.severity is Severity.REQUER_ANALISE_NORMATIVA
    assert "Lei 15.141/2025" in alert.norm_reference


def test_interstice_ending_31_12_2024_does_not_cross():
    snapshot = replace(FASI_2022_2024, end_date=date(2024, 12, 31))
    assert AlertCode.INTERSTICIO_CRUZA_REESTRUTURACAO not in codes(
        verify_process(snapshot, VERSIONS)
    )


# CARR-06
def test_denomination_not_matching_class_shows_expected():
    alerts = verify_process(replace(CLEAN_NEW, target_denomination="Associado"), VERSIONS)
    alert = find(alerts, AlertCode.DENOMINACAO_DIVERGENTE)
    assert alert.severity is Severity.ALERTA
    assert "Adjunto" in alert.message


# CARR-07
def test_missing_structure_skips_structure_checks():
    only_new = (LEI_15141_2025,)
    snapshot = replace(
        FASI_2022_2024,
        current_class="X",
        current_denomination="Nada",
        target_class="Y",
        target_level=9,
        end_date=date(2023, 1, 1),
        opening_date=date(2023, 2, 1),
    )
    alerts = verify_process(snapshot, only_new)
    assert codes(alerts) == [AlertCode.ESTRUTURA_NAO_CADASTRADA]
    assert alerts[0].severity is Severity.REQUER_ANALISE_NORMATIVA


# Edge case: DADOS_INCOMPLETOS
def test_empty_optional_fields_are_listed():
    snapshot = replace(CLEAN_NEW, notes="", resp_name=None, resp_appointment="  ")
    alerts = verify_process(snapshot, VERSIONS)
    alert = find(alerts, AlertCode.DADOS_INCOMPLETOS)
    assert alert.severity is Severity.ALERTA
    assert "observações" in alert.message
    assert "nome do responsável" in alert.message
    assert "portaria de designação do responsável" in alert.message
    assert "cargo do responsável" not in alert.message
    assert codes(alerts) == [AlertCode.DADOS_INCOMPLETOS]


# PROC-10
def test_fasi_2022_2024_case():
    assert select_version(VERSIONS, FASI_2022_2024.end_date) is RES_4644_2015
    interstice = Interstice(FASI_2022_2024.start_date, FASI_2022_2024.end_date)
    assert interstice.months() == 24

    alerts = verify_process(FASI_2022_2024, VERSIONS)

    assert [a for a in alerts if a.severity is Severity.ERRO] == []


# PROC-11
def test_requerimento_2024_2026_case():
    assert select_version(VERSIONS, REQUERIMENTO_2024_2026.end_date) is LEI_15141_2025

    alerts = verify_process(REQUERIMENTO_2024_2026, VERSIONS)

    assert len(alerts) == 5
    assert {a.code: a.severity for a in alerts} == {
        AlertCode.MODALIDADE_INCOMPATIVEL: Severity.ERRO,
        AlertCode.CLASSE_INEXISTENTE_NA_ESTRUTURA: Severity.ERRO,
        AlertCode.DENOMINACAO_DIVERGENTE: Severity.ALERTA,
        AlertCode.INTERSTICIO_NAO_CONCLUIDO: Severity.ALERTA,
        AlertCode.INTERSTICIO_CRUZA_REESTRUTURACAO: Severity.REQUER_ANALISE_NORMATIVA,
    }
    # PROC-04: every alert has a Portuguese message and a norm reference
    for alert in alerts:
        assert alert.message.strip()
        assert alert.norm_reference.strip()
    assert "Associado" in find(alerts, AlertCode.DENOMINACAO_DIVERGENTE).message
    assert "Titular" in find(alerts, AlertCode.DENOMINACAO_DIVERGENTE).message


# PROC-03
def test_snapshot_is_not_modified():
    before = copy.deepcopy(REQUERIMENTO_2024_2026)
    verify_process(REQUERIMENTO_2024_2026, VERSIONS)
    assert REQUERIMENTO_2024_2026 == before
