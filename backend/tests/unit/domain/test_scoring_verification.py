"""VERIF-09..VERIF-13: process-level scoring verification."""

from datetime import date
from decimal import Decimal

import pytest

from app.domain.entities.career import CareerVersion
from app.domain.entities.professor import WorkRegime
from app.domain.entities.scoring import ScoringTableVersion, TableStatus
from app.domain.rules.career_catalog import LEI_15141_2025
from app.domain.rules.process_verification import Severity
from app.domain.rules.scoring_alerts import ScoringAlertCode
from app.domain.rules.scoring_engine import Counters, ScoringResult
from app.domain.rules.scoring_verification import (
    MinimumStatus,
    ScoringContext,
    reference_minimum,
    verify_scoring,
)

D = Decimal
MINIMUMS = {
    "structure": "Res. 4.644/2015-CONSEPE",
    "norm_reference": "Res. 4.644/2015-CONSEPE, art. 12",
    "by_current_class": {"A": 60, "B": 80, "C": 100, "D": 120},
}


def career(name: str) -> CareerVersion:
    return CareerVersion(name, None, None, "norma", classes=())


RES_4644 = career("Res. 4.644/2015-CONSEPE")
LEI_15141 = career("Lei 15.141/2025")


def table(minimums=MINIMUMS) -> ScoringTableVersion:
    return ScoringTableVersion(
        table_id=None,
        name="IFCH",
        valid_from=date(2015, 3, 24),
        valid_to=None,
        norm_reference="Anexo I",
        status=TableStatus.OFICIAL,
        minimums=minimums,
    )


def result(subtotals=None, total="414") -> ScoringResult:
    subs = {g: D(0) for g in range(1, 9)}
    subs.update({g: D(v) for g, v in (subtotals or {}).items()})
    return ScoringResult(
        rows=(),
        group_subtotals=subs,
        total=D(total),
        potential_total=D(0),
        group1_percent=None,
        counters=Counters(0, 0, 0, 0, 0),
        limit_adjustments=(),
    )


def ctx(regime=WorkRegime.DE, klass="C", career_version=RES_4644, version=None) -> ScoringContext:
    return ScoringContext(regime, klass, career_version, version or table())


@pytest.mark.parametrize("regime", [WorkRegime.DE, WorkRegime.H40])
def test_regime_de_ou_40h_sem_extensao_e_pesquisa_alerta(regime):
    alerts = verify_scoring(ctx(regime), result({4: 0, 5: 0}))
    found = [a for a in alerts if a.code is ScoringAlertCode.SEM_EXTENSAO_OU_PESQUISA]
    assert len(found) == 1
    assert found[0].severity is Severity.ALERTA
    assert "art. 13, II" in found[0].norm_reference
    assert found[0].norm_reference.startswith("Res. 4.644/2015")
    assert found[0].message


def test_regime_20h_nao_emite_alerta_de_extensao():
    alerts = verify_scoring(ctx(WorkRegime.H20), result())
    assert ScoringAlertCode.SEM_EXTENSAO_OU_PESQUISA not in {a.code for a in alerts}


@pytest.mark.parametrize("subtotals", [{4: 10}, {5: 3}, {4: 1, 5: 1}])
def test_extensao_ou_pesquisa_presente_nao_alerta(subtotals):
    alerts = verify_scoring(ctx(WorkRegime.DE), result(subtotals))
    assert ScoringAlertCode.SEM_EXTENSAO_OU_PESQUISA not in {a.code for a in alerts}


def test_classe_c_com_414_atinge_minimo_100():
    comparison = reference_minimum(table(), "C", RES_4644, D(414))
    assert comparison.status is MinimumStatus.ATINGE
    assert comparison.minimum == D(100)
    assert comparison.total == D(414)


def test_99_nao_atinge_e_100_atinge():
    assert reference_minimum(table(), "C", RES_4644, D(99)).status is MinimumStatus.NAO_ATINGE
    assert reference_minimum(table(), "C", RES_4644, D(100)).status is MinimumStatus.ATINGE


@pytest.mark.parametrize("klass,minimum", [("A", 60), ("B", 80), ("C", 100), ("D", 120)])
def test_minimo_por_classe_atual(klass, minimum):
    assert reference_minimum(table(), klass, RES_4644, D(0)).minimum == D(minimum)


def test_estrutura_lei_15141_nao_definido_e_alerta():
    comparison = reference_minimum(table(), "C", LEI_15141, D(414))
    assert comparison.status is MinimumStatus.NAO_DEFINIDO
    assert comparison.minimum is None
    alerts = verify_scoring(ctx(career_version=LEI_15141), result())
    found = [a for a in alerts if a.code is ScoringAlertCode.MINIMO_NAO_DEFINIDO]
    assert len(found) == 1
    assert found[0].severity is Severity.REQUER_ANALISE_NORMATIVA
    assert found[0].message
    assert found[0].norm_reference


def test_sem_estrutura_ou_sem_minimos_ou_classe_desconhecida_nao_definido():
    assert reference_minimum(table(), "C", None, D(1)).status is MinimumStatus.NAO_DEFINIDO
    assert reference_minimum(table(None), "C", RES_4644, D(1)).status is MinimumStatus.NAO_DEFINIDO
    assert reference_minimum(table(), "Z", RES_4644, D(1)).status is MinimumStatus.NAO_DEFINIDO


def test_estrutura_4644_com_minimo_nao_emite_minimo_nao_definido():
    alerts = verify_scoring(ctx(), result())
    assert ScoringAlertCode.MINIMO_NAO_DEFINIDO not in {a.code for a in alerts}


def test_verificacao_nao_altera_o_resultado():
    r = result({4: 0})
    before = (dict(r.group_subtotals), r.total)
    verify_scoring(ctx(), r)
    assert (dict(r.group_subtotals), r.total) == before


# NLINK-03: the extension and research alert cites RES-4644-2015-CONSEPE, same reference text
def test_alerta_de_extensao_cita_res_4644():
    [alert] = [
        a
        for a in verify_scoring(ctx(WorkRegime.DE), result({4: 0, 5: 0}))
        if a.code is ScoringAlertCode.SEM_EXTENSAO_OU_PESQUISA
    ]
    assert alert.norm_code == "RES-4644-2015-CONSEPE"
    assert alert.norm_reference == "Res. 4.644/2015-CONSEPE, art. 13, II"


# NLINK-03, NMIN-01: the undefined minimum cites RES-4644-2015-CONSEPE and has no number
def test_minimo_nao_definido_cita_res_4644_na_lei_15141():
    assert reference_minimum(table(), "C", LEI_15141_2025, D(414)).minimum is None
    assert (
        reference_minimum(table(), "C", LEI_15141_2025, D(414)).status
        is MinimumStatus.NAO_DEFINIDO
    )
    [alert] = [
        a
        for a in verify_scoring(ctx(career_version=LEI_15141_2025), result())
        if a.code is ScoringAlertCode.MINIMO_NAO_DEFINIDO
    ]
    assert alert.norm_code == "RES-4644-2015-CONSEPE"
    assert alert.norm_reference == "Res. 4.644/2015-CONSEPE, art. 12"
