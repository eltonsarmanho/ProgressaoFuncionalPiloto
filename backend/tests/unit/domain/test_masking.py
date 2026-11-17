"""EXT-07: personal identifiers are masked; names, SIAPE and document numbers stay."""

import pytest

from app.domain.rules.masking import mask_identifiers


def masked(text: str) -> str:
    return mask_identifiers(text).text


@pytest.mark.parametrize("cpf", ["123.456.789-09", "12345678909"])
def test_cpf_with_and_without_punctuation_becomes_marker(cpf):
    assert masked(f"CPF: {cpf}, residente em Belém") == "CPF: [CPF], residente em Belém"


def test_bare_cpf_inside_a_longer_digit_run_is_kept():
    assert masked("código 123456789012") == "código 123456789012"
    assert masked("CNPJ 12345678000195") == "CNPJ 12345678000195"


@pytest.mark.parametrize(
    "text",
    [
        "RG: 1234567 SSP/PA",
        "R.G. nº 1.234.567-8",
        "Identidade n° 1234567 - SSP/PA",
        "Registro Geral 1234567-X",
        "rg 12.345.678-9",
    ],
)
def test_rg_number_becomes_marker_and_label_stays(text):
    result = masked(f"Portador do {text}, nascido em 1980")
    assert "[RG]" in result
    assert result.endswith(", nascido em 1980")
    for leaked in ("1234567", "12.345.678", "SSP"):
        assert leaked not in result


def test_rg_label_is_kept_next_to_the_marker():
    assert masked("RG: 1234567 SSP/PA") == "RG: [RG]"


def test_email_becomes_marker():
    assert masked("Contato: maria.souza+ufpa@exemplo.com.br.") == "Contato: [EMAIL]."


@pytest.mark.parametrize(
    "phone",
    [
        "(91) 98888-7777",
        "91 98888-7777",
        "+55 91 98888-7777",
        "+55 (91) 98888-7777",
        "55 (91) 98888-7777",
        "(91) 3201-1234",
        "(91)32011234",
        "91 3201-1234",
        "+55 91 3201-1234",
        "98888-7777",
    ],
)
def test_brazilian_phone_variants_become_marker(phone):
    assert masked(f"Telefone {phone} para contato") == "Telefone [TELEFONE] para contato"


def test_several_identifiers_in_one_text_are_all_masked():
    text = "CPF 123.456.789-09, e-mail a@b.com, fone (91) 98888-7777, RG 1234567 SSP/PA"
    result = mask_identifiers(text)
    assert result.text == "CPF [CPF], e-mail [EMAIL], fone [TELEFONE], RG [RG]"
    assert result.counts == {"CPF": 1, "EMAIL": 1, "TELEFONE": 1, "RG": 1}


def test_text_without_identifiers_is_returned_equal_with_no_counts():
    text = "Declaramos que a professora participou da banca."
    result = mask_identifiers(text)
    assert result.text == text
    assert result.counts == {}


def test_original_text_is_not_changed():
    original = "CPF 123.456.789-09"
    snapshot = str(original)
    result = mask_identifiers(original)
    assert original == snapshot
    assert result.text != original


def test_proper_names_and_siape_stay():
    text = "A servidora Maria da Silva Souza, SIAPE 1234567, matrícula 7654321."
    assert masked(text) == text


@pytest.mark.parametrize(
    "text",
    [
        "Portaria nº 3686/2024",
        "Processo 23073.036388/2025-95",
        "CNPJ 12.345.678/0001-95",
        "Emitido em 23/03/2026 e 23.03.2026 e 2026-03-23",
        "no ano de 2022",
        "CH Disciplina: 68 h - CH Docente: 68 h",
        "Período letivo 2022.2",
        "DOI 10.1016/j.jss.2020.110000",
        "ISSN 1234-5678",
        "vigência 2024-2025",
        "semestre 68 2024-2025",
        "Resolução 4.644/2015, art. 5º, §1º",
    ],
)
def test_other_numbers_must_stay(text):
    assert masked(text) == text
