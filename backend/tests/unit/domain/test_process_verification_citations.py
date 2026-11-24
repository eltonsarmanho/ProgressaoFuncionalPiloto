"""NLINK-01, NLINK-03, NLINK-06 and NMOV-05: the norm code cited by each process alert.

The structures here are synthetic copies of the catalogue ones, linked to a synthetic norm
code, so the code that comes from the structure is told apart from the fixed ones.
"""

import copy
from dataclasses import replace
from datetime import date

import pytest

from app.domain.entities.career import CareerClass, Modality
from app.domain.rules.career_catalog import LEI_15141_2025, RES_4644_2015
from app.domain.rules.process_verification import AlertCode, ProcessSnapshot, verify_process

SYNTHETIC_CODE = "NORMA-SINTETICA-ESTRUTURA"
SYNTHETIC_NEW = replace(LEI_15141_2025, norm_code=SYNTHETIC_CODE)
SYNTHETIC_VERSIONS = (replace(RES_4644_2015, norm_code="NORMA-SINTETICA-ANTIGA"), SYNTHETIC_NEW)
# The catalogue structures are linked to their norms (NLINK-02); a structure with no code is built.
UNLINKED_VERSIONS = (
    replace(RES_4644_2015, norm_code=None),
    replace(LEI_15141_2025, norm_code=None),
)

CLEAN = ProcessSnapshot(
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
)

PROMOTION_JUMP = dict(
    modality=Modality.PROMOCAO,
    current_class="A",
    current_denomination="Assistente",
    current_level=1,
    target_class="C",
    target_denomination="Associado",
    target_level=1,
)

SCENARIOS = {
    AlertCode.CLASSE_INEXISTENTE_NA_ESTRUTURA: dict(target_level=5, current_level=4),
    AlertCode.DENOMINACAO_DIVERGENTE: dict(target_denomination="Associado"),
    AlertCode.INTERSTICIO_INSUFICIENTE: dict(end_date=date(2027, 1, 31)),
    AlertCode.INTERSTICIO_NAO_CONCLUIDO: dict(opening_date=date(2027, 1, 31)),
    AlertCode.ESTRUTURA_NAO_CADASTRADA: dict(
        start_date=date(2030, 1, 1), end_date=date(2032, 1, 1), opening_date=date(2032, 2, 1)
    ),
    AlertCode.INTERSTICIO_CRUZA_REESTRUTURACAO: dict(start_date=date(2024, 12, 1)),
    AlertCode.INTERSTICIO_DATAS_INVALIDAS: dict(end_date=date(2025, 1, 15)),
}

EXPECTED_CODE = {
    AlertCode.CLASSE_INEXISTENTE_NA_ESTRUTURA: SYNTHETIC_CODE,
    AlertCode.DENOMINACAO_DIVERGENTE: SYNTHETIC_CODE,
    AlertCode.INTERSTICIO_INSUFICIENTE: SYNTHETIC_CODE,
    AlertCode.INTERSTICIO_NAO_CONCLUIDO: "RES-4644-2015-CONSEPE",
    AlertCode.ESTRUTURA_NAO_CADASTRADA: "RES-4644-2015-CONSEPE",
    AlertCode.INTERSTICIO_CRUZA_REESTRUTURACAO: "LEI-12772-2012",
    # not in the design table; cites the first norm of its reference (Res. 4.644, art. 5º)
    AlertCode.INTERSTICIO_DATAS_INVALIDAS: "RES-4644-2015-CONSEPE",
}


def only(alerts, code):
    matches = [a for a in alerts if a.code is code]
    assert len(matches) == 1, [a.code for a in alerts]
    return matches[0]


def versions_for(code):
    # ESTRUTURA_NAO_CADASTRADA needs no covering version: only the old structure
    if code is AlertCode.ESTRUTURA_NAO_CADASTRADA:
        return SYNTHETIC_VERSIONS[:1]
    return SYNTHETIC_VERSIONS


@pytest.mark.parametrize("code", list(SCENARIOS), ids=lambda c: c.value)
def test_each_alert_cites_its_norm_code_with_synthetic_linked_structure(code):
    alert = only(verify_process(replace(CLEAN, **SCENARIOS[code]), versions_for(code)), code)
    assert alert.norm_code == EXPECTED_CODE[code]


@pytest.mark.parametrize(
    ("modality", "changes"),
    [
        (Modality.PROMOCAO, PROMOTION_JUMP),
        (Modality.PROGRESSAO, dict(target_level=3)),
    ],
    ids=["promotion", "progression"],
)
def test_both_modality_alerts_cite_lei_12772_with_synthetic_linked_structure(modality, changes):
    snapshot = replace(CLEAN, **{**changes, "modality": modality})
    alert = only(verify_process(snapshot, SYNTHETIC_VERSIONS), AlertCode.MODALIDADE_INCOMPATIVEL)
    assert alert.norm_code == "LEI-12772-2012"


@pytest.mark.parametrize(
    "code",
    [
        AlertCode.CLASSE_INEXISTENTE_NA_ESTRUTURA,
        AlertCode.DENOMINACAO_DIVERGENTE,
        AlertCode.INTERSTICIO_INSUFICIENTE,
    ],
    ids=lambda c: c.value,
)
def test_structure_without_norm_code_gives_null_code_and_same_reference(code):
    snapshot = replace(CLEAN, **SCENARIOS[code])
    unlinked = only(verify_process(snapshot, UNLINKED_VERSIONS), code)
    linked = only(verify_process(snapshot, SYNTHETIC_VERSIONS), code)

    assert unlinked.norm_code is None
    assert unlinked.norm_reference == LEI_15141_2025.norm_reference
    assert linked.norm_reference == unlinked.norm_reference


# NMOV-05: the structure's new denomination is used at the next verification
def test_changed_denomination_in_synthetic_structure_yields_divergence_without_changing_process():
    process = replace(
        CLEAN,
        current_class="C",
        current_denomination="Associado",
        target_class="C",
        target_denomination="Associado",
    )
    before = copy.deepcopy(process)
    assert AlertCode.DENOMINACAO_DIVERGENTE not in [
        a.code for a in verify_process(process, SYNTHETIC_VERSIONS)
    ]

    renamed = replace(
        SYNTHETIC_NEW,
        classes=tuple(
            CareerClass(c.code, ("Denominação Sintética",), c.levels, c.promotion_min_months)
            if c.code == "C"
            else c
            for c in SYNTHETIC_NEW.classes
        ),
    )
    alert = only(
        verify_process(process, (SYNTHETIC_VERSIONS[0], renamed)),
        AlertCode.DENOMINACAO_DIVERGENTE,
    )

    assert "Denominação Sintética" in alert.message
    assert '"Associado"' in alert.message
    assert process == before
    assert process.current_denomination == "Associado"
