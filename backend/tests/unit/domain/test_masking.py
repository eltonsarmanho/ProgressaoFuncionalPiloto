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


# --- VER-05: leaks found by the independent verification --------------------------------------


@pytest.mark.parametrize(
    "cpf",
    [
        "123 456 789 09",
        "123.456.789 09",
        "123 456 789-09",
        "123.456.789-\n09",
        "123.456.\n789-09",
        "123 456 789\n09",
    ],
)
def test_cpf_with_spaces_or_split_by_a_line_break_becomes_marker(cpf):
    result = mask_identifiers(f"CPF {cpf}, residente em Belém")
    assert result.text == "CPF [CPF], residente em Belém"
    assert result.counts == {"CPF": 1}


@pytest.mark.parametrize(
    "phone",
    ["3201-7777", "3201 7777", "91 3201 7777", "91 3201-7777"],
)
def test_landline_without_area_code_or_with_spaces_becomes_marker(phone):
    text = f"Contato: fone {phone} no horário comercial"
    assert masked(text) == "Contato: fone [TELEFONE] no horário comercial"


def test_landline_without_area_code_and_with_a_label_is_masked_after_telefone():
    assert masked("Telefone: 3201-7777.") == "Telefone: [TELEFONE]."


@pytest.mark.parametrize("ci", ["CI 1234567", "C.I. nº 1.234.567", "CI: 12345678-9", "ci 1234567"])
def test_ci_number_becomes_marker_and_label_stays(ci):
    result = masked(f"Portador da {ci}, nascido em 1980")
    assert "[RG]" in result
    assert result.endswith(", nascido em 1980")
    assert result.startswith("Portador da ")
    for leaked in ("1234567", "1.234.567", "12345678"):
        assert leaked not in result


def test_unlabeled_rg_in_the_formatted_pattern_becomes_marker():
    assert masked("Maria Souza, 12.345.678-9, SSP/PA") == "Maria Souza, [RG], SSP/PA"


@pytest.mark.parametrize(
    "text",
    [
        "CI nº 45/2025 da direção",
        "CI 123456/2024",
        "Emitido em 12/03/2025 às 14:30",
        "das 14:30 às 16:00",
        "Processo 23073.012345/2025-11",
        "Processo 23073.036388/2025-95",
        "página 12 de 40",
        "pp. 2345-2350",
        "ISSN 2318-1990",
        "e-ISSN 2318 1990",
        "SIAPE 1234567",
        "SIAPE: 1234567-8",
        "vigência 2024-2025",
        "semestre 68 2024-2025",
        "CNPJ 12.345.678/0001-95",
        "carga horária 120 060 horas",
        "12 03 2025",
    ],
)
def test_false_positive_control_keeps_dates_hours_processes_pages_and_siape(text):
    assert masked(text) == text
