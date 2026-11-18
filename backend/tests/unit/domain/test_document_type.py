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


# REAL-19: articles with Resumo and Abstract, or with one marker and an article section.
ARTIGO_RESUMO_ABSTRACT = """
Anais do Simpósio Fictício de Computação
Um estudo inventado sobre nada
Resumo. Este trabalho inventado não estuda nada.
Abstract. This invented paper studies nothing.
"""

ARTIGO_PALAVRAS_CHAVE_SEM_HIFEN = """
Revista Fictícia de Exemplos
Palavras chave: exemplo; teste.
1. Introdução
Este artigo inventado apresenta um exemplo.
"""

ARTIGO_RESUMO_INTRODUCAO = """
Um estudo inventado
Resumo: texto inventado.
1 Introdução
Texto do artigo inventado.
"""


@pytest.mark.parametrize(
    "text", [ARTIGO_RESUMO_ABSTRACT, ARTIGO_PALAVRAS_CHAVE_SEM_HIFEN, ARTIGO_RESUMO_INTRODUCAO]
)
def test_article_with_resumo_and_abstract_or_a_marker_and_a_section_is_an_article(text):
    assert detect_document_type(text) is T.ARTIGO


@pytest.mark.parametrize(
    "text",
    [
        "Texto qualquer com um Resumo da reunião.",
        "1. Introdução\nRelatório interno.\nReferências: lista de documentos internos.",
        "Palavras-chave: apenas isto.",
    ],
)
def test_one_marker_or_only_article_sections_are_not_an_article(text):
    assert detect_document_type(text) is T.OUTRO


# REAL-20: the declaration says what the professor did, not what word comes first.
DECLARACAO_BANCA_COM_ORIENTADOR_ANTES = """
DECLARAÇÃO
Declaramos que o Prof. Dr. Carlos Imaginario, orientador do discente Joao Inventado,
participou como membro da banca examinadora do Trabalho de Conclusão de Curso de Maria Teste,
defendido em 12 de março de 2024.
"""

DECLARACAO_ORIENTACAO_COM_BANCA_DEPOIS = """
DECLARAÇÃO
Declaro que Ana Ficticia Lima foi orientadora do discente Pedro Teste, cujo trabalho foi
apresentado à banca de avaliação em 2023.
"""


def test_banca_declaration_that_names_an_advisor_before_the_participation_is_a_banca_declaration():
    assert detect_document_type(DECLARACAO_BANCA_COM_ORIENTADOR_ANTES) is T.DECLARACAO_BANCA


def test_orientation_declaration_that_mentions_a_banca_afterwards_stays_an_orientation_one():
    assert detect_document_type(DECLARACAO_ORIENTACAO_COM_BANCA_DEPOIS) is T.DECLARACAO_ORIENTACAO


# CER-01: certificates written in English (invented person and policy brief). The PDF text of
# the real case lost the "ti" glyphs ("cerfy", "parcipated") and "CERTIFICATE" comes last.
CERTIFICATE_EN_LOST_GLYPHS = """
This is to cerfy, for all due purposes, that Maria Exemplo Silva, from the Universidade
Federal Exemplar, parcipated in the development of the policy brief "Open Data for Cities",
dedicang six weeks (18 hours) to this acvity as part of the iniaves of the Example Chair on
Open Data.
Chair Coordinator
CERTIFICATE
"""

CERTIFICATE_EN_SAME_LINE_ENDING = (
    "Maria Exemplo Silva took part in the policy brief Open Data for Cities, 18 hours. "
    "Chair Coordinator CERTIFICATE"
)


@pytest.mark.parametrize(
    "text",
    [
        CERTIFICATE_EN_LOST_GLYPHS,
        CERTIFICATE_EN_SAME_LINE_ENDING,
        "This is to certify that Maria Exemplo Silva attended the workshop, 8 hours.",
        "THIS IS TO CERTIFY THAT Maria Exemplo Silva attended the workshop.",
        "We hereby certify that Maria Exemplo Silva completed the course, 20 hours.",
        "The committee is hereby certifying the attendance of Maria Exemplo Silva, 4 hours.",
        "Certificate of Participation\nMaria Exemplo Silva, workshop on open data, 6 hours.",
        "Certificate of completion awarded to Maria Exemplo Silva for the course on data.",
        "Maria Exemplo Silva received this certificate of attendance for the 2025 seminar.",
        "Maria Exemplo Silva, workshop on open data, 6 hours.\nCERTIFICATE\nChair Coordinator",
    ],
)
def test_english_certificates_are_certificates(text):
    assert detect_document_type(text) is T.CERTIFICADO


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        # "certificate" inside running text of an article stays an article
        (ARTIGO_EN + "\nThe server sends a certificate to the client.", T.ARTIGO),
        (ARTIGO_EN + "\nOnly the signed certificate", T.ARTIGO),
        (ARTIGO_EN + "\nCERTIFICATE\nReferences", T.ARTIGO),
        # a bare word inside a sentence of a plain text is not a certificate
        ("The certificate expired last week and nobody renewed it.", T.OUTRO),
        ("Relatório com o certificate pinning descrito no capítulo 3.", T.OUTRO),
        # the portaria keeps its type
        (PORTARIA, T.PORTARIA),
    ],
)
def test_english_certificate_wording_does_not_turn_other_documents_into_certificates(
    text, expected
):
    assert detect_document_type(text) is expected
