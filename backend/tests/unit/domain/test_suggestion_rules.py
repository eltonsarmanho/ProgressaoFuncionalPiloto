"""CLS-02, CLS-03, CLS-04, CLS-10: taxonomy to scoring item, row by row from the design table."""

import pytest

from app.domain.entities.activity import Level
from app.domain.entities.extraction import TaxonomyCode as T
from app.domain.rules.suggestion_rules import (
    Item,
    Suggestion,
    confirm_extension_course,
    suggest_item,
)

NO_ITEM = None

# (taxonomy, principal, alternatives), transcribed from "Regras de sugestão" in design.md.
DESIGN_TABLE = [
    (T.ORIENTACAO_POS_DOUTORADO, "II.1", []),
    (T.ORIENTACAO_DOUTORADO, "II.2", []),
    (T.COORIENTACAO_DOUTORADO, "II.4", []),
    (T.ORIENTACAO_MESTRADO, "II.3", []),
    (T.COORIENTACAO_MESTRADO, "II.5", []),
    (T.ORIENTACAO_ESPECIALIZACAO, "II.6", []),
    (T.ORIENTACAO_TCC_GRADUACAO, "II.7", []),
    (T.COORIENTACAO_TCC_GRADUACAO, NO_ITEM, []),
    (T.ORIENTACAO_EM_ANDAMENTO_DOUTORADO, "II.14", []),
    (T.ORIENTACAO_EM_ANDAMENTO_MESTRADO, "II.15", []),
    (T.ORIENTACAO_EM_ANDAMENTO_TCC, "II.16", []),
    (T.ORIENTACAO_PROJETO_INSTITUCIONAL, "II.8", ["II.9"]),
    (T.ORIENTACAO_ESTAGIO, "II.12", []),
    (T.ORIENTACAO_MONITORIA, "II.13", []),
    (T.BANCA_DOUTORADO, "III.1", []),
    (T.BANCA_MESTRADO, "III.2", []),
    (T.BANCA_ESPECIALIZACAO, "III.3", []),
    (T.BANCA_TCC_GRADUACAO, "III.4", []),
    (T.BANCA_CONCURSO_SUBSTITUTO, "III.5", []),
    (T.BANCA_CONCURSO_EFETIVO, "III.6", []),
    (T.BANCA_QUALIFICACAO, "III.7", []),
    (T.BANCA_SELECAO_POS, "III.8", ["III.12"]),
    (T.BANCA_SELECAO_BOLSAS, "III.9", ["III.12"]),
    (T.BANCA_PROCESSO_SELETIVO, "III.11", ["III.12"]),
    (T.EXTENSAO_PROJETO_COORDENACAO, "IV.1", []),
    (T.EXTENSAO_PROJETO_PARTICIPACAO, "IV.2", []),
    (T.EXTENSAO_CURSO_COORDENACAO, "IV.3", []),
    (T.EXTENSAO_CURSO_MINISTRANTE, "IV.4", ["IV.5"]),
    (T.EXTENSAO_EVENTO_COORDENACAO, "IV.6", []),
    (T.EXTENSAO_EVENTO_MINISTRANTE, "IV.7", []),
    (T.PESQUISA_PROJETO_COORDENACAO, "V.1", []),
    (T.PESQUISA_GRUPO_COORDENACAO, "V.2", []),
    (T.PESQUISA_GRUPO_MEMBRO, "V.3", []),
    (T.PESQUISA_BOLSA_PRODUTIVIDADE, "V.4", []),
    (T.FUNCAO_DIRETOR_FACULDADE, "VI.6", ["VI.3"]),
    (T.FUNCAO_VICE_DIRETOR_FACULDADE, "VI.7", []),
    (T.FUNCAO_COORDENADOR_CURSO_GRADUACAO, "VI.7", []),
    (T.COMISSAO_ADMINISTRACAO_SUPERIOR, "VI.10", ["VI.14"]),
    (T.COMISSAO_NDE_MEMBRO, "VI.10", ["VI.14"]),
    (T.COMISSAO_UNIDADE, "VI.12", ["VI.14"]),
    (T.COLEGIADO_MEMBRO, "VI.13", []),
    (T.CURSO_ESPECIALIZACAO_CONCLUIDO, "VII.7", []),
    (T.CURSO_APERFEICOAMENTO_CONCLUIDO, "VII.8", ["VII.9"]),
    (T.CURSO_EXTENSAO_CONCLUIDO, "VII.9", []),
    (T.CURSO_CONCLUIDO, "VII.10", []),
    (T.PARTICIPACAO_EVENTO, "VII.10", []),
    (T.TREINAMENTO_INTERNO, "VII.10", []),
    (T.ESTAGIO_CAPACITACAO, "VII.11", []),
    (T.LIVRO_COM_PARECERISTAS, "VIII.1", []),
    (T.LIVRO_SEM_PARECERISTAS, "VIII.2", []),
    (T.CAPITULO_INTERNACIONAL, "VIII.3", []),
    (T.CAPITULO_NACIONAL, "VIII.4", []),
    (T.ARTIGO_INTERNACIONAL_INDEXADO, "VIII.11", ["VIII.13"]),
    (T.ARTIGO_NACIONAL_INDEXADO, "VIII.12", ["VIII.13"]),
    (T.ARTIGO_NAO_INDEXADO, "VIII.13", []),
    (T.TRABALHO_COMPLETO_CONGRESSO, "VIII.23", ["VIII.12"]),
    (T.COMUNICACAO_COM_RESUMO, "VIII.24", []),
    (T.COMUNICACAO_SEM_RESUMO, "VIII.25", []),
    (T.APRESENTACAO_TRABALHO_INTERNACIONAL, "VIII.26", []),
    (T.APRESENTACAO_TRABALHO_NACIONAL, "VIII.27", []),
    (T.PALESTRA, "VIII.28", []),
    (T.PATENTE_DEPOSITADA, "VIII.35", []),
    (T.PATENTE_CONCEDIDA, "VIII.36", []),
    (T.REGISTRO_SOFTWARE, "VIII.63", []),
    (T.CONSULTORIA_AD_HOC, "VIII.66", []),
    (T.OUTRA, NO_ITEM, []),
]

ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7, "VIII": 8}
GROUP_I_ONLY = {T.DISCIPLINA_MINISTRADA}


def item(label: str) -> Item:
    group, number = label.split(".")
    return Item(ROMAN[group], int(number))


@pytest.mark.parametrize(("taxonomy", "principal", "alternatives"), DESIGN_TABLE)
def test_rule_matches_the_design_table_row(taxonomy, principal, alternatives):
    suggestion = suggest_item(taxonomy)
    assert isinstance(suggestion, Suggestion)
    assert suggestion.principal == (item(principal) if principal else None)
    assert list(suggestion.alternatives) == [item(a) for a in alternatives]


def test_every_taxonomy_code_has_a_rule():
    covered = {row[0] for row in DESIGN_TABLE} | GROUP_I_ONLY
    assert covered == set(T)
    for taxonomy in T:
        assert isinstance(suggest_item(taxonomy), Suggestion)


def test_every_rule_cites_its_source():
    for taxonomy in T:
        assert suggest_item(taxonomy).source_note.strip() != ""


def test_rule_with_item_cites_the_annex_group_and_item():
    note = suggest_item(T.BANCA_TCC_GRADUACAO).source_note
    assert note == "Res. 4.644/2015, Anexo I, Grupo III, item 4"
    assert suggest_item(T.PALESTRA).source_note == "Res. 4.644/2015, Anexo I, Grupo VIII, item 28"


@pytest.mark.parametrize("taxonomy", [T.COORIENTACAO_TCC_GRADUACAO, T.OUTRA])
def test_taxonomy_without_item_has_no_principal_and_no_alternatives(taxonomy):
    suggestion = suggest_item(taxonomy)
    assert suggestion.principal is None
    assert suggestion.alternatives == ()


def test_palestra_is_viii_28_without_alternatives():
    suggestion = suggest_item(T.PALESTRA)
    assert suggestion.principal == Item(8, 28)
    assert suggestion.alternatives == ()


@pytest.mark.parametrize(
    "taxonomy", [T.TREINAMENTO_INTERNO, T.PARTICIPACAO_EVENTO, T.CURSO_CONCLUIDO]
)
def test_training_event_and_plain_course_are_vii_10(taxonomy):
    assert suggest_item(taxonomy).principal == Item(7, 10)


def test_discipline_in_graduation_is_i_1():
    suggestion = suggest_item(T.DISCIPLINA_MINISTRADA, level=Level.GRADUACAO)
    assert suggestion.principal == Item(1, 1)
    assert suggestion.alternatives == ()
    assert suggestion.source_note == "Res. 4.644/2015, Anexo I, Grupo I, item 1"


def test_discipline_in_postgraduation_is_i_2():
    suggestion = suggest_item(T.DISCIPLINA_MINISTRADA, level=Level.POS_GRADUACAO)
    assert suggestion.principal == Item(1, 2)
    assert suggestion.alternatives == ()
    assert suggestion.source_note == "Res. 4.644/2015, Anexo I, Grupo I, item 2"


def test_discipline_without_level_suggests_i_1_with_i_2_as_alternative():
    suggestion = suggest_item(T.DISCIPLINA_MINISTRADA)
    assert suggestion.principal == Item(1, 1)
    assert suggestion.alternatives == (Item(1, 2),)


def test_level_does_not_change_the_other_taxonomies():
    assert suggest_item(T.BANCA_MESTRADO, level=Level.GRADUACAO) == suggest_item(T.BANCA_MESTRADO)


# CLS-10: a course counts as extension only when the document says "extensão".


def test_extension_course_with_the_word_stays_extension_course():
    text = "Certificamos a conclusão do Curso de Extensão em Dados Abertos."
    assert confirm_extension_course(T.CURSO_EXTENSAO_CONCLUIDO, text) == T.CURSO_EXTENSAO_CONCLUIDO
    assert suggest_item(T.CURSO_EXTENSAO_CONCLUIDO).principal == Item(7, 9)


def test_extension_course_without_the_word_becomes_plain_course():
    text = "Certificamos a conclusão do curso de Dados Abertos, com 40 horas."
    downgraded = confirm_extension_course(T.CURSO_EXTENSAO_CONCLUIDO, text)
    assert downgraded == T.CURSO_CONCLUIDO
    assert suggest_item(downgraded).principal == Item(7, 10)


@pytest.mark.parametrize(
    "text", ["CURSO DE EXTENSAO", "curso de EXTENSÃO", "Extensão universitária"]
)
def test_extension_check_ignores_accent_and_case(text):
    assert confirm_extension_course(T.CURSO_EXTENSAO_CONCLUIDO, text) == T.CURSO_EXTENSAO_CONCLUIDO


def test_extension_course_with_empty_text_becomes_plain_course():
    assert confirm_extension_course(T.CURSO_EXTENSAO_CONCLUIDO, "") == T.CURSO_CONCLUIDO


@pytest.mark.parametrize("taxonomy", [t for t in T if t is not T.CURSO_EXTENSAO_CONCLUIDO])
def test_other_taxonomies_pass_through_unchanged(taxonomy):
    assert confirm_extension_course(taxonomy, "sem a palavra") == taxonomy
    assert confirm_extension_course(taxonomy, "curso de extensão") == taxonomy
