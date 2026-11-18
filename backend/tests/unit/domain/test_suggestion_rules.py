"""CLS-02..04, CLS-10, MAP-01, MAP-02: taxonomy to scoring item, official table numbering."""

import pytest

from app.domain.entities.activity import Level
from app.domain.entities.extraction import DocumentType as DT
from app.domain.entities.extraction import TaxonomyCode as T
from app.domain.rules.suggestion_rules import (
    Item,
    Suggestion,
    confirm_board_document,
    confirm_extension_course,
    confirm_extension_project,
    is_dismissal_clause,
    suggest_item,
)

NO_ITEM = None

# (taxonomy, principal, alternatives): "Regras de sugestão" of inteligencia-documental with the
# numbering changes of the tabela-oficial design.
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
    (T.BANCA_SELECAO_POS, "III.8", []),
    (T.BANCA_SELECAO_BOLSAS, "III.9", []),
    (T.BANCA_PROCESSO_SELETIVO, NO_ITEM, []),
    (T.EXTENSAO_PROJETO_COORDENACAO, "IV.1", []),
    (T.EXTENSAO_PROJETO_PARTICIPACAO, "IV.2", []),
    (T.EXTENSAO_CURSO_COORDENACAO, "IV.3", []),
    (T.EXTENSAO_CURSO_MINISTRANTE, "IV.4", ["IV.5"]),
    (T.EXTENSAO_EVENTO_COORDENACAO, "IV.6", []),
    (T.EXTENSAO_EVENTO_MINISTRANTE, NO_ITEM, []),
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
    (T.ARTIGO_INTERNACIONAL_INDEXADO, "VIII.9", ["VIII.11"]),
    (T.ARTIGO_NACIONAL_INDEXADO, "VIII.10", ["VIII.11"]),
    (T.ARTIGO_NAO_INDEXADO, "VIII.11", []),
    (T.TRABALHO_COMPLETO_CONGRESSO, "VIII.19", ["VIII.10"]),
    (T.COMUNICACAO_COM_RESUMO, "VIII.20", []),
    (T.COMUNICACAO_SEM_RESUMO, "VIII.21", []),
    (T.APRESENTACAO_TRABALHO_INTERNACIONAL, "VIII.22", []),
    (T.APRESENTACAO_TRABALHO_NACIONAL, "VIII.23", []),
    (T.PALESTRA, "VIII.24", []),
    (T.PATENTE_DEPOSITADA, "VIII.29", []),
    (T.PATENTE_CONCEDIDA, "VIII.30", []),
    (T.REGISTRO_SOFTWARE, "VIII.33", []),
    (T.CONSULTORIA_AD_HOC, "VIII.36", []),
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


def test_rule_with_item_cites_the_official_table_group_and_item():
    note = suggest_item(T.BANCA_TCC_GRADUACAO).source_note
    assert note == "Tabela oficial de pontuação da UFPA, Grupo III, item 4"
    assert (
        suggest_item(T.PALESTRA).source_note
        == "Tabela oficial de pontuação da UFPA, Grupo VIII, item 24"
    )


@pytest.mark.parametrize(
    "taxonomy",
    [
        T.COORIENTACAO_TCC_GRADUACAO,
        T.OUTRA,
        T.BANCA_PROCESSO_SELETIVO,
        T.EXTENSAO_EVENTO_MINISTRANTE,
    ],
)
def test_taxonomy_without_item_has_no_principal_and_no_alternatives(taxonomy):
    suggestion = suggest_item(taxonomy)
    assert suggestion.principal is None
    assert suggestion.alternatives == ()


def test_palestra_is_viii_24_without_alternatives():
    suggestion = suggest_item(T.PALESTRA)
    assert suggestion.principal == Item(8, 24)
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
    assert suggestion.source_note == "Tabela oficial de pontuação da UFPA, Grupo I, item 1"


def test_discipline_in_postgraduation_is_i_2():
    suggestion = suggest_item(T.DISCIPLINA_MINISTRADA, level=Level.POS_GRADUACAO)
    assert suggestion.principal == Item(1, 2)
    assert suggestion.alternatives == ()
    assert suggestion.source_note == "Tabela oficial de pontuação da UFPA, Grupo I, item 2"


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


# MAP-01: the 13 Group VIII types that changed number, with the retained book and chapter rules.
GROUP_VIII_RENUMBERED = {
    T.ARTIGO_INTERNACIONAL_INDEXADO: (9, [11]),
    T.ARTIGO_NACIONAL_INDEXADO: (10, [11]),
    T.ARTIGO_NAO_INDEXADO: (11, []),
    T.TRABALHO_COMPLETO_CONGRESSO: (19, [10]),
    T.COMUNICACAO_COM_RESUMO: (20, []),
    T.COMUNICACAO_SEM_RESUMO: (21, []),
    T.APRESENTACAO_TRABALHO_INTERNACIONAL: (22, []),
    T.APRESENTACAO_TRABALHO_NACIONAL: (23, []),
    T.PALESTRA: (24, []),
    T.PATENTE_DEPOSITADA: (29, []),
    T.PATENTE_CONCEDIDA: (30, []),
    T.REGISTRO_SOFTWARE: (33, []),
    T.CONSULTORIA_AD_HOC: (36, []),
}


def test_the_thirteen_group_viii_types_use_the_official_numbers():
    assert len(GROUP_VIII_RENUMBERED) == 13
    for taxonomy, (number, alternatives) in GROUP_VIII_RENUMBERED.items():
        suggestion = suggest_item(taxonomy)
        assert suggestion.principal == Item(8, number), taxonomy
        assert list(suggestion.alternatives) == [Item(8, n) for n in alternatives], taxonomy


@pytest.mark.parametrize(
    ("taxonomy", "number"),
    [
        (T.LIVRO_COM_PARECERISTAS, 1),
        (T.LIVRO_SEM_PARECERISTAS, 2),
        (T.CAPITULO_INTERNACIONAL, 3),
        (T.CAPITULO_NACIONAL, 4),
    ],
)
def test_books_and_chapters_stay_in_viii_1_to_viii_4(taxonomy, number):
    assert suggest_item(taxonomy).principal == Item(8, number)


# MAP-02: no suggestion points to an item the official table does not have (III.12, IV.7, III.11).
@pytest.mark.parametrize("taxonomy", [t for t in T if t is not T.DISCIPLINA_MINISTRADA])
def test_no_rule_points_to_the_removed_items(taxonomy):
    suggestion = suggest_item(taxonomy)
    used = {suggestion.principal, *suggestion.alternatives} - {None}
    assert not used & {Item(3, 11), Item(3, 12), Item(4, 7)}


def test_selection_board_types_have_no_alternative():
    assert suggest_item(T.BANCA_SELECAO_POS).alternatives == ()
    assert suggest_item(T.BANCA_SELECAO_BOLSAS).alternatives == ()


def test_types_without_a_table_item_cite_the_official_table_as_the_reason():
    for taxonomy in (T.BANCA_PROCESSO_SELETIVO, T.EXTENSAO_EVENTO_MINISTRANTE):
        assert "tabela oficial" in suggest_item(taxonomy).source_note


# REAL-10: a clause that dispenses the professor from a function is not an activity.
FUNCTION_TAXONOMIES = [
    T.FUNCAO_DIRETOR_FACULDADE,
    T.FUNCAO_VICE_DIRETOR_FACULDADE,
    T.FUNCAO_COORDENADOR_CURSO_GRADUACAO,
    T.COMISSAO_ADMINISTRACAO_SUPERIOR,
    T.COMISSAO_NDE_MEMBRO,
    T.COMISSAO_UNIDADE,
    T.COLEGIADO_MEMBRO,
]


@pytest.mark.parametrize("taxonomy", FUNCTION_TAXONOMIES)
@pytest.mark.parametrize(
    "clause",
    [
        "DISPENSAR a Profa. Fulana de Tal da função de Diretora da Faculdade",
        "Fica dispensado o servidor da função de Coordenador, a partir de 09/08/2026",
        "EXONERAR Fulana de Tal do cargo de Diretora",
        "destituir o docente da comissão",
        "Fica sem efeito a designação de Fulana de Tal como membro do colegiado",
    ],
)
def test_clause_that_dismisses_the_professor_is_not_an_activity(taxonomy, clause):
    assert is_dismissal_clause(taxonomy, clause) is True


@pytest.mark.parametrize("taxonomy", FUNCTION_TAXONOMIES)
@pytest.mark.parametrize(
    "clause",
    [
        "DESIGNAR a Profa. Fulana de Tal para exercer a função de Vice-Diretora",
        "Fica designado o servidor como membro titular do NDE",
        "NOMEAR Fulana de Tal Coordenadora do curso",
        "Dispensar Beltrano da função de Diretor e designar Fulana de Tal como Vice-Diretora",
        "",
    ],
)
def test_designation_or_mixed_or_empty_clause_is_kept(taxonomy, clause):
    assert is_dismissal_clause(taxonomy, clause) is False


@pytest.mark.parametrize("taxonomy", [t for t in T if t not in FUNCTION_TAXONOMIES])
def test_dismissal_wording_in_other_types_is_not_a_dismissal_clause(taxonomy):
    assert is_dismissal_clause(taxonomy, "Dispensa de licitação para o curso") is False


# REAL-12: extension projects need the word "extensão" (or the table's wording) in the document.
PROJECTS = [T.EXTENSAO_PROJETO_COORDENACAO, T.EXTENSAO_PROJETO_PARTICIPACAO]


@pytest.mark.parametrize("taxonomy", PROJECTS)
def test_project_without_the_extension_wording_has_no_scoring_item(taxonomy):
    text = "Certificamos a participação no projeto Policy Brief sobre Dados, com 18 horas."
    downgraded = confirm_extension_project(taxonomy, text)
    assert downgraded is T.OUTRA
    assert suggest_item(downgraded).principal is NO_ITEM


@pytest.mark.parametrize("taxonomy", PROJECTS)
@pytest.mark.parametrize(
    "text",
    [
        "Projeto de Extensão Dados Abertos",
        "PROJETO DE EXTENSAO DADOS ABERTOS",
        "Pró-Reitoria de Extensão certifica a participação no projeto",
    ],
)
def test_project_with_the_extension_wording_keeps_its_type(taxonomy, text):
    assert confirm_extension_project(taxonomy, text) is taxonomy


@pytest.mark.parametrize("taxonomy", [t for t in T if t not in PROJECTS])
def test_project_check_passes_every_other_type_through(taxonomy):
    assert confirm_extension_project(taxonomy, "sem a palavra") is taxonomy


def test_extension_project_item_numbers_stay_iv_1_and_iv_2_with_the_wording():
    assert suggest_item(T.EXTENSAO_PROJETO_COORDENACAO).principal == Item(4, 1)
    assert suggest_item(T.EXTENSAO_PROJETO_PARTICIPACAO).principal == Item(4, 2)


# REAL-18: no banca from a seminar evaluation form.
FORM = "Ficha de avaliação de seminário 2. Avaliador 1: Prof. Ana. Avaliador 2: Prof. Carlos."
BOARDS = [t for t in T if t.value.startswith("BANCA_")]


@pytest.mark.parametrize("taxonomy", BOARDS)
def test_board_from_a_seminar_form_of_unknown_type_has_no_item(taxonomy):
    downgraded = confirm_board_document(taxonomy, DT.OUTRO, FORM)
    assert downgraded is T.OUTRA
    assert suggest_item(downgraded).principal is NO_ITEM


@pytest.mark.parametrize("document_type", [t for t in DT if t is not DT.OUTRO])
def test_board_from_a_recognized_document_type_is_kept(document_type):
    assert confirm_board_document(T.BANCA_MESTRADO, document_type, FORM) is T.BANCA_MESTRADO


def test_board_from_other_text_of_unknown_type_is_kept():
    text = "Declaro que a banca examinadora aprovou a dissertação."
    assert confirm_board_document(T.BANCA_MESTRADO, DT.OUTRO, text) is T.BANCA_MESTRADO


@pytest.mark.parametrize("taxonomy", [t for t in T if t not in BOARDS])
def test_non_board_types_pass_through_the_board_check(taxonomy):
    assert confirm_board_document(taxonomy, DT.OUTRO, FORM) is taxonomy
