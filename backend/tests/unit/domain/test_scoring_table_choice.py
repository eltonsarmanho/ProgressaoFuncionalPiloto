"""SEL-03, SEL-05, SEL-06, SEL-07: verification of the table chosen for a process."""

from dataclasses import replace
from datetime import date
from uuid import uuid4

from app.domain.entities.scoring import ScoringTableVersion, TableStatus
from app.domain.rules.process_verification import Severity
from app.domain.rules.scoring_alerts import ScoringAlertCode
from app.domain.rules.scoring_table_choice import pick_unit_default, verify_table_choice

UNIT = uuid4()
OTHER_UNIT = uuid4()
END = date(2024, 11, 23)


def version(status=TableStatus.OFICIAL, valid_from=date(2015, 3, 24), valid_to=None, ref="Anexo I"):
    return ScoringTableVersion(
        table_id=None,
        name="v",
        valid_from=valid_from,
        valid_to=valid_to,
        norm_reference=ref,
        status=status,
    )


def codes(alerts):
    return [a.code for a in alerts]


def test_sem_versao_gera_tabela_nao_encontrada_requer_analise():
    alerts = verify_table_choice(None, (), UNIT, END)
    assert codes(alerts) == [ScoringAlertCode.TABELA_NAO_ENCONTRADA]
    assert alerts[0].severity is Severity.REQUER_ANALISE_NORMATIVA
    assert alerts[0].message
    assert alerts[0].norm_reference


def test_tabela_da_propria_unidade_oficial_e_vigente_nao_gera_alerta():
    assert verify_table_choice(version(), (UNIT,), UNIT, END) == []


def test_tabela_de_outra_unidade_gera_alerta():
    alerts = verify_table_choice(version(), (OTHER_UNIT,), UNIT, END)
    assert codes(alerts) == [ScoringAlertCode.TABELA_DE_OUTRA_UNIDADE]
    assert alerts[0].severity is Severity.ALERTA
    assert alerts[0].norm_reference == "Anexo I"


def test_tabela_associada_a_varias_unidades_incluindo_a_do_docente_nao_alerta():
    assert verify_table_choice(version(), (OTHER_UNIT, UNIT), UNIT, END) == []


def test_versao_pendente_gera_tabela_pendente_requer_analise():
    alerts = verify_table_choice(version(TableStatus.PENDENTE_VALIDACAO), (UNIT,), UNIT, END)
    assert codes(alerts) == [ScoringAlertCode.TABELA_PENDENTE_VALIDACAO]
    assert alerts[0].severity is Severity.REQUER_ANALISE_NORMATIVA


def test_versao_que_nao_cobre_data_final_gera_fora_de_vigencia():
    ended = version(valid_to=date(2024, 11, 22))
    alerts = verify_table_choice(ended, (UNIT,), UNIT, END)
    assert codes(alerts) == [ScoringAlertCode.TABELA_FORA_DE_VIGENCIA]
    assert alerts[0].severity is Severity.ALERTA


def test_versao_que_ainda_nao_comecava_gera_fora_de_vigencia():
    future = version(valid_from=date(2024, 11, 24))
    assert codes(verify_table_choice(future, (UNIT,), UNIT, END)) == [
        ScoringAlertCode.TABELA_FORA_DE_VIGENCIA
    ]


def test_vigencia_termina_exatamente_na_data_final_cobre():
    assert verify_table_choice(version(valid_to=END), (UNIT,), UNIT, END) == []


def test_varios_problemas_geram_todos_os_alertas():
    bad = version(TableStatus.PENDENTE_VALIDACAO, valid_to=date(2020, 1, 1))
    assert set(codes(verify_table_choice(bad, (OTHER_UNIT,), UNIT, END))) == {
        ScoringAlertCode.TABELA_DE_OUTRA_UNIDADE,
        ScoringAlertCode.TABELA_PENDENTE_VALIDACAO,
        ScoringAlertCode.TABELA_FORA_DE_VIGENCIA,
    }


def pick(default, *, archived=False, table_units=(UNIT,), unit=UNIT):
    return pick_unit_default(
        default, table_archived=archived, table_unit_ids=table_units, unit_id=unit
    )


def test_versao_em_uso_que_passa_nas_tres_guardas_e_devolvida():
    default = version()
    assert pick(default) is default


def test_versao_em_uso_fora_de_vigencia_ainda_e_devolvida():
    expired = version(valid_from=date(2010, 1, 1), valid_to=date(2012, 12, 31))
    assert pick(expired) is expired


def test_sem_versao_em_uso_devolve_none():
    assert pick(None) is None


def test_versao_substituida_devolve_none():
    superseded = replace(version(), superseded_by_id=uuid4())
    assert pick(superseded) is None


def test_tabela_arquivada_devolve_none():
    assert pick(version(), archived=True) is None


def test_unidade_fora_da_tabela_devolve_none():
    assert pick(version(), table_units=(OTHER_UNIT,)) is None
    assert pick(version(), table_units=()) is None
