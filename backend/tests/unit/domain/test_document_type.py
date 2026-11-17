"""EXT-09: document type chosen by keywords, on synthetic texts in the style of real ones."""

import pytest

from app.domain.entities.extraction import DocumentType as T
from app.domain.rules.document_type import detect_document_type, is_seminar_evaluation_form

DECLARACAO_BANCA_TCC = """
UNIVERSIDADE FEDERAL EXEMPLAR
DECLARAÇÃO
Declaramos, para os devidos fins, que a Profa. Dra. Ana Fictícia Lima participou como Membro
da Banca Examinadora do Trabalho de Conclusão de Curso intitulado "Estudo de caso fictício",
de autoria de Joao Inventado, orientado pelo Prof. Carlos Imaginario, realizado em 12/03/2024.
Conforme a Portaria nº 1234/2024 da Faculdade.
"""

DECLARACAO_BANCA_DISSERTACAO = """
DECLARAÇÃO
Declaro para os devidos fins que Ana Ficticia Lima participou como membro da banca examinadora
da Dissertação de Mestrado de Pedro Teste, defendida em 20 de agosto de 2023.
"""

DECLARACAO_ORIENTACAO = """
DECLARAÇÃO
Declaramos para os devidos fins que o Prof. Dr. Carlos Imaginario atuou como ORIENTADOR do
Trabalho de Conclusão de Curso de Joao Inventado, defendido perante banca examinadora em 2024.
"""

DECLARACAO_COORIENTACAO = """
DECLARAÇÃO
Declaro para os devidos fins que Ana Ficticia Lima foi CO-ORIENTADORA da Dissertação de
Pedro Teste, aprovada pela banca examinadora em 2023.
"""

DECLARACAO_DISCIPLINAS = """
DECLARAÇÃO
Declaramos que Ana Ficticia Lima ministrou, no período letivo 2022.2, os seguintes
componentes curriculares: Algoritmos Fictícios - CH Disciplina: 68 h - CH Docente: 68 h.
"""

ATA_DEFESA_UFPA = """
UNIVERSIDADE FEDERAL EXEMPLAR
ATA DA DEFESA PÚBLICA DO TRABALHO DE CONCLUSÃO DE CURSO
Aos 12 dias do mês de março de 2024, reuniu-se a banca examinadora composta por Ana Ficticia Lima,
Carlos Imaginario e Beatriz Exemplo. O trabalho foi aprovado.
"""

ATA_DEFESA_SIPAC = """
SIPAC - Sistema Integrado
Ata de Defesa de Dissertação nº 55
A banca examinadora, após a arguição do candidato, considerou o trabalho aprovado.
"""

CERTIFICADO_PALESTRA = """
Certificamos que Ana Ficticia Lima apresentou a palestra "Tema de exemplo" no Seminário
Fictício de Computação, em 10 de maio de 2023, com carga horária de 2 horas.
"""

CERTIFICADO_CURSO = """
CERTIFICADO
Esse certificado reconhece que Ana Ficticia Lima Concluiu com êxito o curso
Introdução a Exemplos, com carga horária de 21 horas.
"""

CERTIFICADO_SEMINARIO = """
A Comissão Organizadora certifica que Ana Ficticia Lima participou do seminário
Tópicos de Exemplo, realizado em 2022, totalizando 8 horas.
"""

PORTARIA = """
SERVIÇO PÚBLICO FEDERAL
PORTARIA Nº 4321/2024
O REITOR DA UNIVERSIDADE FEDERAL EXEMPLAR, no uso de suas atribuições, RESOLVE:
Designar Ana Ficticia Lima para exercer a função de Coordenadora do Curso Fictício.
"""

ARTIGO_EN = """
Journal of Fictitious Computing, ISSN 1234-5678
Title of an invented article
Abstract: this invented paper studies nothing. Keywords: example, test.
DOI: 10.9999/jfc.2023.0001
"""

ARTIGO_PT = """
Revista Fictícia de Computação ISSN 8765-4321
Um artigo inventado
Resumo: este artigo inventado não estuda nada. Palavras-chave: exemplo; teste.
"""

REGISTRO_SOFTWARE = """
INSTITUTO NACIONAL DA PROPRIEDADE INDUSTRIAL
Certificado de Registro de Programa de Computador
Processo nº BR 51 2023 000000-0. Título: Sistema Fictício.
"""


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (DECLARACAO_BANCA_TCC, T.DECLARACAO_BANCA),
        (DECLARACAO_BANCA_DISSERTACAO, T.DECLARACAO_BANCA),
        (DECLARACAO_ORIENTACAO, T.DECLARACAO_ORIENTACAO),
        (DECLARACAO_COORIENTACAO, T.DECLARACAO_ORIENTACAO),
        (DECLARACAO_DISCIPLINAS, T.DECLARACAO_DISCIPLINAS),
        (ATA_DEFESA_UFPA, T.ATA_DEFESA),
        (ATA_DEFESA_SIPAC, T.ATA_DEFESA),
        (CERTIFICADO_PALESTRA, T.CERTIFICADO),
        (CERTIFICADO_CURSO, T.CERTIFICADO),
        (CERTIFICADO_SEMINARIO, T.CERTIFICADO),
        (PORTARIA, T.PORTARIA),
        (ARTIGO_EN, T.ARTIGO),
        (ARTIGO_PT, T.ARTIGO),
        (REGISTRO_SOFTWARE, T.REGISTRO_SOFTWARE),
    ],
)
def test_synthetic_text_of_each_type_gives_the_expected_type(text, expected):
    assert detect_document_type(text) is expected


@pytest.mark.parametrize(
    "text",
    [
        "",
        "   \n ",
        "Lista de compras: arroz, feijão e café. Nada de documento acadêmico aqui.",
        "Relatório interno sobre o andamento das obras no prédio principal.",
    ],
)
def test_text_without_any_keyword_is_other(text):
    assert detect_document_type(text) is T.OUTRO


def test_matching_ignores_case_and_accents():
    assert detect_document_type(DECLARACAO_BANCA_TCC.upper()) is T.DECLARACAO_BANCA
    stripped = "declaracao. declaramos que x participou como membro da banca examinadora do tcc."
    assert detect_document_type(stripped) is T.DECLARACAO_BANCA


def test_banca_declaration_that_cites_a_portaria_stays_a_banca_declaration():
    text = "PORTARIA Nº 1 RESOLVE\n" + DECLARACAO_BANCA_TCC
    assert detect_document_type(text) is T.DECLARACAO_BANCA


def test_banca_declaration_naming_the_advisor_later_stays_a_banca_declaration():
    text = (
        "Declaramos que X participou como membro da banca examinadora do TCC de Y. "
        "Orientador: Prof. Z."
    )
    assert detect_document_type(text) is T.DECLARACAO_BANCA


def test_article_that_mentions_a_digital_certificate_later_stays_an_article():
    text = ARTIGO_EN + "\n" + "x " * 400 + "uses a certificado digital to sign messages."
    assert detect_document_type(text) is T.ARTIGO


def test_single_article_marker_is_not_enough():
    assert detect_document_type("Texto qualquer com um Resumo da reunião.") is T.OUTRO


def test_software_registration_wins_over_the_certificate_word():
    assert detect_document_type(REGISTRO_SOFTWARE) is T.REGISTRO_SOFTWARE


def test_word_ata_inside_other_words_does_not_make_a_defense_minutes():
    text = "Data da defesa: a banca examinadora aprovou. Estatais e datas diversas."
    assert detect_document_type(text) is T.OUTRO


# REAL-18: a seminar evaluation form is not a defense board.
FICHA_SEMINARIO = """
UNIVERSIDADE FEDERAL EXEMPLAR
FICHA DE AVALIAÇÃO DE SEMINÁRIO 2
Discente: Joao Inventado. Título do seminário: Estudo de caso fictício.
Avaliador 1: Prof. Ana Ficticia Lima  Nota: 9,0
Avaliador 2: Prof. Carlos Imaginario  Nota: 8,5
Data da apresentação: 12/05/2023
"""


def test_seminar_evaluation_form_is_other_and_is_recognized_as_a_form():
    assert detect_document_type(FICHA_SEMINARIO) is T.OUTRO
    assert is_seminar_evaluation_form(FICHA_SEMINARIO) is True


@pytest.mark.parametrize(
    "text",
    [ATA_DEFESA_UFPA, DECLARACAO_BANCA_DISSERTACAO, CERTIFICADO_SEMINARIO, PORTARIA, ""],
)
def test_other_documents_are_not_seminar_evaluation_forms(text):
    assert is_seminar_evaluation_form(text) is False


def test_evaluation_wording_without_a_seminar_is_not_a_seminar_form():
    assert is_seminar_evaluation_form("Ficha de avaliação de estágio probatório") is False
